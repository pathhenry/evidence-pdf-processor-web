#!/usr/bin/env python3
"""
證據文件批次處理核心邏輯
支援批次生成多個證據文件PDF
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from evidence_pdf_converter import EvidencePDFConverter

class BatchEvidenceProcessor:
    """批次證據文件處理器"""
    
    def __init__(self):
        self.converter = EvidencePDFConverter()
        self.batch_jobs = {}  # 存儲批次任務
    
    def add_job(self, job_id: str, files: List[str], label_text: str, output_dir: str = None):
        """
        添加批次處理任務
        
        Args:
            job_id: 任務ID（如：原證1、聲證2）
            files: 檔案列表
            label_text: 標籤文字
            output_dir: 輸出目錄（可選）
        """
        if not files:
            return False
            
        self.batch_jobs[job_id] = {
            'files': files,
            'label_text': label_text,
            'output_dir': output_dir,
            'status': 'pending',
            'output_file': None,
            'error': None
        }
        return True
    
    def remove_job(self, job_id: str):
        """移除批次處理任務"""
        if job_id in self.batch_jobs:
            del self.batch_jobs[job_id]
            return True
        return False
    
    def clear_all_jobs(self):
        """清空所有任務"""
        self.batch_jobs.clear()
    
    def get_job_status(self, job_id: str) -> str:
        """取得任務狀態"""
        if job_id in self.batch_jobs:
            return self.batch_jobs[job_id]['status']
        return 'not_found'
    
    def get_all_jobs_status(self) -> Dict[str, str]:
        """取得所有任務狀態"""
        return {job_id: job['status'] for job_id, job in self.batch_jobs.items()}
    
    def generate_batch_output_filename(self, job_id: str, files: List[str], output_dir: str = None) -> str:
        """生成批次處理的輸出檔名"""
        if output_dir:
            output_path = Path(output_dir)
        else:
            # 使用第一個檔案的目錄
            output_path = Path(files[0]).parent
        
        # 確保輸出目錄存在
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成檔名
        filename = f"{job_id}.pdf"
        return str(output_path / filename)
    
    def process_single_job(self, job_id: str) -> bool:
        """
        處理單一任務
        
        Returns:
            bool: 處理成功返回True，失敗返回False
        """
        if job_id not in self.batch_jobs:
            return False
        
        job = self.batch_jobs[job_id]
        job['status'] = 'processing'
        
        try:
            # 生成輸出檔案路徑
            output_file = self.generate_batch_output_filename(
                job_id, job['files'], job['output_dir']
            )
            
            # 執行轉換
            self.converter.convert(job['files'], output_file, job['label_text'])
            
            # 更新任務狀態
            job['status'] = 'completed'
            job['output_file'] = output_file
            job['error'] = None
            
            return True
            
        except Exception as e:
            # 處理失敗
            job['status'] = 'failed'
            job['error'] = str(e)
            return False
    
    def process_all_jobs(self, progress_callback=None) -> Dict[str, bool]:
        """
        處理所有任務
        
        Args:
            progress_callback: 進度回調函數 callback(job_id, status, current, total)
            
        Returns:
            Dict[str, bool]: 各任務的處理結果
        """
        results = {}
        total_jobs = len(self.batch_jobs)
        current_job = 0
        
        for job_id in self.batch_jobs.keys():
            current_job += 1
            
            # 呼叫進度回調
            if progress_callback:
                progress_callback(job_id, 'processing', current_job, total_jobs)
            
            # 處理任務
            success = self.process_single_job(job_id)
            results[job_id] = success
            
            # 呼叫完成回調
            if progress_callback:
                status = 'completed' if success else 'failed'
                progress_callback(job_id, status, current_job, total_jobs)
        
        return results
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """取得任務詳細資料"""
        return self.batch_jobs.get(job_id)
    
    def get_completed_jobs(self) -> List[str]:
        """取得已完成的任務列表"""
        return [job_id for job_id, job in self.batch_jobs.items() 
                if job['status'] == 'completed']
    
    def get_failed_jobs(self) -> List[str]:
        """取得失敗的任務列表"""
        return [job_id for job_id, job in self.batch_jobs.items() 
                if job['status'] == 'failed']
    
    def get_pending_jobs(self) -> List[str]:
        """取得待處理的任務列表"""
        return [job_id for job_id, job in self.batch_jobs.items() 
                if job['status'] == 'pending']
    
    def generate_summary_report(self) -> str:
        """生成處理結果摘要報告"""
        total = len(self.batch_jobs)
        completed = len(self.get_completed_jobs())
        failed = len(self.get_failed_jobs())
        pending = len(self.get_pending_jobs())
        
        report = f"""批次處理結果摘要
===================
總任務數：{total}
已完成：{completed}
失敗：{failed}
待處理：{pending}

"""
        
        if completed > 0:
            report += "已完成的任務：\n"
            for job_id in self.get_completed_jobs():
                job = self.batch_jobs[job_id]
                report += f"  ✓ {job_id} -> {job['output_file']}\n"
            report += "\n"
        
        if failed > 0:
            report += "失敗的任務：\n"
            for job_id in self.get_failed_jobs():
                job = self.batch_jobs[job_id]
                report += f"  ✗ {job_id}: {job['error']}\n"
        
        return report


def create_numbered_jobs(prefix: str, start_num: int, end_num: int, 
                        files_dict: Dict[int, List[str]], output_dir: str = None) -> BatchEvidenceProcessor:
    """
    創建編號批次任務
    
    Args:
        prefix: 前綴（如：原證、聲證、書證）
        start_num: 起始編號
        end_num: 結束編號
        files_dict: 檔案字典 {編號: [檔案列表]}
        output_dir: 輸出目錄
        
    Returns:
        BatchEvidenceProcessor: 配置好的批次處理器
    """
    processor = BatchEvidenceProcessor()
    
    for num in range(start_num, end_num + 1):
        job_id = f"{prefix}{num}"
        label_text = job_id
        
        if num in files_dict and files_dict[num]:
            processor.add_job(job_id, files_dict[num], label_text, output_dir)
    
    return processor


if __name__ == "__main__":
    # 測試範例
    processor = BatchEvidenceProcessor()
    
    # 添加測試任務
    processor.add_job("原證1", ["test1.jpg"], "原證1")
    processor.add_job("原證2", ["test2.jpg", "test3.jpg"], "原證2")
    
    # 處理所有任務
    def progress_callback(job_id, status, current, total):
        print(f"[{current}/{total}] {job_id}: {status}")
    
    results = processor.process_all_jobs(progress_callback)
    
    print("\n" + processor.generate_summary_report())
