#!/usr/bin/env python3
"""
證據文件PDF處理程式 - 網頁版
"""

import os
import sys
import uuid
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 導入核心處理模組
from evidence_pdf_converter import EvidencePDFConverter
from batch_processor import BatchEvidenceProcessor

app = Flask(__name__)

# 配置設定（適配 Render 環境）
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))  # 100MB 上傳限制
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'evidence-pdf-converter-2024')

# 使用系統臨時目錄（Render 環境中更可靠）
temp_dir = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = os.path.join(temp_dir, 'evidence_uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(temp_dir, 'evidence_output')

# 啟用 CORS
CORS(app)

# 確保上傳和輸出目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 允許的檔案類型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'tif', 'bmp', 'gif', 'pdf'}

def allowed_file(filename):
    """檢查檔案類型是否允許"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """清理超過 1 小時的舊檔案"""
    now = datetime.now()
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        for filepath in Path(folder).iterdir():
            if filepath.is_file():
                # 檔案超過 1 小時就刪除
                if (now.timestamp() - filepath.stat().st_mtime) > 3600:
                    try:
                        filepath.unlink()
                    except:
                        pass

@app.route('/')
def index():
    """首頁"""
    cleanup_old_files()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """處理檔案上傳"""
    try:
        # 檢查請求中是否有檔案
        if 'files' not in request.files:
            return jsonify({'error': '沒有選擇檔案'}), 400
        
        files = request.files.getlist('files')
        evidence_type = request.form.get('evidenceType', '原證')
        evidence_number = request.form.get('evidenceNumber', '1')
        
        if not files or files[0].filename == '':
            return jsonify({'error': '沒有選擇檔案'}), 400
        
        # 生成唯一的工作 ID
        job_id = str(uuid.uuid4())
        job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
        os.makedirs(job_folder, exist_ok=True)
        
        uploaded_files = []
        
        # 保存上傳的檔案
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # 避免檔名衝突
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name, ext = os.path.splitext(filename)
                safe_filename = f"{name}_{timestamp}{ext}"
                
                filepath = os.path.join(job_folder, safe_filename)
                file.save(filepath)
                uploaded_files.append(filepath)
        
        if not uploaded_files:
            return jsonify({'error': '沒有有效的檔案'}), 400
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'files_count': len(uploaded_files),
            'evidence_type': evidence_type,
            'evidence_number': evidence_number
        })
        
    except Exception as e:
        return jsonify({'error': f'上傳失敗: {str(e)}'}), 500

@app.route('/process', methods=['POST'])
def process_files():
    """處理證據檔案轉換"""
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        evidence_type = data.get('evidence_type', '原證')
        evidence_number = data.get('evidence_number', '1')
        
        if not job_id:
            return jsonify({'error': '缺少工作 ID'}), 400
        
        job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
        if not os.path.exists(job_folder):
            return jsonify({'error': '找不到上傳的檔案'}), 404
        
        # 取得上傳的檔案
        uploaded_files = [
            os.path.join(job_folder, f) 
            for f in os.listdir(job_folder) 
            if os.path.isfile(os.path.join(job_folder, f))
        ]
        
        if not uploaded_files:
            return jsonify({'error': '沒有找到檔案'}), 404
        
        # 創建輸出目錄
        output_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
        os.makedirs(output_folder, exist_ok=True)
        
        # 處理檔案
        converter = EvidencePDFConverter()
        label_text = f"{evidence_type}{evidence_number}"
        
        # 生成輸出檔名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{label_text}_{timestamp}.pdf"
        output_path = os.path.join(output_folder, output_filename)
        
        # 轉換檔案
        converter.convert(uploaded_files, output_path, label_text)
        
        if os.path.exists(output_path):
            return jsonify({
                'success': True,
                'job_id': job_id,
                'filename': output_filename,
                'download_url': url_for('download_file', job_id=job_id, filename=output_filename)
            })
        else:
            return jsonify({'error': '處理失敗'}), 500
            
    except Exception as e:
        return jsonify({'error': f'處理失敗: {str(e)}'}), 500

@app.route('/batch_process', methods=['POST'])
def batch_process():
    """批次處理多個證據檔案"""
    try:
        data = request.get_json()
        jobs = data.get('jobs', [])
        
        if not jobs:
            return jsonify({'error': '沒有要處理的任務'}), 400
        
        # 創建批次處理器
        processor = BatchEvidenceProcessor()
        batch_id = str(uuid.uuid4())
        batch_output_folder = os.path.join(app.config['OUTPUT_FOLDER'], batch_id)
        os.makedirs(batch_output_folder, exist_ok=True)
        
        results = []
        
        for job in jobs:
            job_id = job.get('job_id')
            evidence_type = job.get('evidence_type', '原證')
            evidence_number = job.get('evidence_number', '1')
            
            job_folder = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
            if not os.path.exists(job_folder):
                results.append({
                    'job_id': job_id,
                    'success': False,
                    'error': '找不到上傳的檔案'
                })
                continue
            
            uploaded_files = [
                os.path.join(job_folder, f) 
                for f in os.listdir(job_folder) 
                if os.path.isfile(os.path.join(job_folder, f))
            ]
            
            if not uploaded_files:
                results.append({
                    'job_id': job_id,
                    'success': False,
                    'error': '沒有找到檔案'
                })
                continue
            
            try:
                # 處理單個任務
                label_text = f"{evidence_type}{evidence_number}"
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"{label_text}_{timestamp}.pdf"
                output_path = os.path.join(batch_output_folder, output_filename)
                
                converter = EvidencePDFConverter()
                converter.convert(uploaded_files, output_path, label_text)
                
                results.append({
                    'job_id': job_id,
                    'success': True,
                    'filename': output_filename
                })
                
            except Exception as e:
                results.append({
                    'job_id': job_id,
                    'success': False,
                    'error': str(e)
                })
        
        # 統計結果
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        return jsonify({
            'success': True,
            'batch_id': batch_id,
            'results': results,
            'summary': f'{success_count}/{total_count} 個檔案處理成功',
            'download_url': url_for('download_batch', batch_id=batch_id) if success_count > 0 else None
        })
        
    except Exception as e:
        return jsonify({'error': f'批次處理失敗: {str(e)}'}), 500

@app.route('/download/<job_id>/<filename>')
def download_file(job_id, filename):
    """下載單個檔案"""
    try:
        output_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
        file_path = os.path.join(output_folder, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': '檔案不存在'}), 404
            
    except Exception as e:
        return jsonify({'error': f'下載失敗: {str(e)}'}), 500

@app.route('/download_batch/<batch_id>')
def download_batch(batch_id):
    """下載批次處理結果（打包成 ZIP）"""
    try:
        import zipfile
        import tempfile
        
        batch_folder = os.path.join(app.config['OUTPUT_FOLDER'], batch_id)
        if not os.path.exists(batch_folder):
            return jsonify({'error': '批次檔案不存在'}), 404
        
        # 創建臨時 ZIP 檔案
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
            for filename in os.listdir(batch_folder):
                file_path = os.path.join(batch_folder, filename)
                if os.path.isfile(file_path):
                    zipf.write(file_path, filename)
        
        return send_file(
            temp_zip.name, 
            as_attachment=True, 
            download_name=f'證據檔案批次_{batch_id[:8]}.zip'
        )
        
    except Exception as e:
        return jsonify({'error': f'下載失敗: {str(e)}'}), 500

@app.route('/download_batch_by_jobs', methods=['POST'])
def download_batch_by_jobs():
    """根據 job_ids 批次下載檔案（打包成 ZIP）"""
    try:
        import zipfile
        import tempfile
        
        data = request.get_json()
        job_ids = data.get('job_ids', [])
        
        if not job_ids:
            return jsonify({'error': '沒有提供 job_ids'}), 400
        
        # 創建臨時 ZIP 檔案
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
            for job_id in job_ids:
                job_folder = os.path.join(app.config['OUTPUT_FOLDER'], job_id)
                if os.path.exists(job_folder):
                    for filename in os.listdir(job_folder):
                        file_path = os.path.join(job_folder, filename)
                        if os.path.isfile(file_path):
                            # 使用檔案名作為 ZIP 內的路徑，避免重複
                            zipf.write(file_path, filename)
        
        return send_file(
            temp_zip.name, 
            as_attachment=True, 
            download_name=f'證據檔案批次_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
        
    except Exception as e:
        return jsonify({'error': f'批次下載失敗: {str(e)}'}), 500

@app.route('/health')
def health():
    """健康檢查端點（Render 要求）"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.1 Web'
    }), 200

@app.route('/status')
def status():
    """系統狀態"""
    try:
        upload_count = len([f for f in Path(app.config['UPLOAD_FOLDER']).rglob('*') if f.is_file()])
        output_count = len([f for f in Path(app.config['OUTPUT_FOLDER']).rglob('*') if f.is_file()])
        
        return jsonify({
            'status': 'running',
            'upload_files': upload_count,
            'output_files': output_count,
            'version': '2.1 Web',
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'output_folder': app.config['OUTPUT_FOLDER']
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'version': '2.1 Web'
        }), 500

if __name__ == '__main__':
    # 本地開發環境
    port = int(os.environ.get('PORT', 5003))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)