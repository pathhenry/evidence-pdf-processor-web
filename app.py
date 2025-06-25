#!/usr/bin/env python3
"""
證據文件PDF處理程式 - 網頁版
"""

import os
import sys
import uuid
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, url_for
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
        for item in Path(folder).iterdir():
            try:
                if not item.exists():
                    continue
                mtime = item.stat().st_mtime
                if (now.timestamp() - mtime) > 3600:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Error cleaning up {item}: {e}")

@app.route('/')
def index():
    """首頁"""
    cleanup_old_files()
    return render_template('index.html')

@app.route('/batch_process', methods=['POST'])
def batch_process():
    """批次處理多個證據檔案"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': '沒有選擇檔案'}), 400

        files = request.files.getlist('files')
        evidence_ids = request.form.getlist('evidence_ids')

        if not files or not evidence_ids or len(files) != len(evidence_ids):
            return jsonify({'error': '檔案和證據ID不匹配'}), 400

        batch_id = str(uuid.uuid4())
        batch_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
        batch_output_folder = os.path.join(app.config['OUTPUT_FOLDER'], batch_id)
        os.makedirs(batch_upload_folder, exist_ok=True)
        os.makedirs(batch_output_folder, exist_ok=True)

        # 整理上傳的檔案
        uploaded_files_map = {}
        for i, file in enumerate(files):
            if file and allowed_file(file.filename):
                job_id, _ = evidence_ids[i].rsplit('_', 1)
                if job_id not in uploaded_files_map:
                    uploaded_files_map[job_id] = []
                
                filename = secure_filename(file.filename)
                filepath = os.path.join(batch_upload_folder, f"{evidence_ids[i]}_{filename}")
                file.save(filepath)
                uploaded_files_map[job_id].append(filepath)

        if not uploaded_files_map:
            return jsonify({'error': '沒有有效的檔案'}), 400

        # 使用 BatchEvidenceProcessor 處理
        processor = BatchEvidenceProcessor()
        for job_id, file_list in uploaded_files_map.items():
            processor.add_job(job_id, file_list, job_id, batch_output_folder)

        processor.process_all_jobs()

        # 構建返回結果
        results = []
        processed_files = []
        for job_id, details in processor.batch_jobs.items():
            if details['status'] == 'completed':
                results.append({
                    'evidenceId': job_id,
                    'success': True,
                    'filename': os.path.basename(details['output_file'])
                })
                processed_files.append(details['output_file'])
            else:
                results.append({
                    'evidenceId': job_id,
                    'success': False,
                    'error': details['error']
                })

        # 打包ZIP
        zip_download_url = None
        if processed_files:
            zip_filename = f'證據檔案批次_{batch_id[:8]}.zip'
            zip_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in processed_files:
                    zipf.write(file_path, os.path.basename(file_path))
            zip_download_url = url_for('download_batch', filename=zip_filename)

        return jsonify({
            'success': True,
            'results': results,
            'summary': f'{len(processed_files)}/{len(uploaded_files_map)} 個任務處理成功',
            'download_url': zip_download_url
        })

    except Exception as e:
        return jsonify({'error': f'批次處理失敗: {str(e)}'}), 500

@app.route('/download_batch/<filename>')
def download_batch(filename):
    """下載批次處理的ZIP檔案"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': '檔案不存在'}), 404
    except Exception as e:
        return jsonify({'error': f'下載失敗: {str(e)}'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200

@app.route('/status')
def status():
    try:
        upload_count = len([f for f in Path(app.config['UPLOAD_FOLDER']).rglob('*') if f.is_file()])
        output_count = len([f for f in Path(app.config['OUTPUT_FOLDER']).rglob('*') if f.is_file()])
        return jsonify({
            'status': 'running',
            'upload_files': upload_count,
            'output_files': output_count,
            'upload_folder': app.config['UPLOAD_FOLDER'],
            'output_folder': app.config['OUTPUT_FOLDER']
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)