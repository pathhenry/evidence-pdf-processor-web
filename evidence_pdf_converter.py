#!/usr/bin/env python3
"""
證據文件PDF轉換程式
自動將檔案轉換為A4格式的PDF，並加上標籤文字
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Union
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
import PyPDF2

class EvidencePDFConverter:
    """證據文件PDF轉換器"""
    
    def __init__(self):
        self.A4_WIDTH = A4[0]  # 595.276 points
        self.A4_HEIGHT = A4[1]  # 841.890 points
        self.LABEL_WIDTH = 1 * cm  # 約28 points (修改為1cm寬)
        self.LABEL_HEIGHT = 3 * cm  # 約85 points (修改為3cm高)
        self.MARGIN = 0.5 * cm
        
    def is_image_file(self, filepath: str) -> bool:
        """檢查是否為圖片檔案"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'}
        return Path(filepath).suffix.lower() in image_extensions
    
    def is_pdf_file(self, filepath: str) -> bool:
        """檢查是否為PDF檔案"""
        return Path(filepath).suffix.lower() == '.pdf'
    
    def get_optimal_image_size(self, image_width: int, image_height: int) -> Tuple[float, float, bool]:
        """
        計算圖片在A4頁面上的最佳大小
        返回: (寬度, 高度, 是否需要旋轉)
        """
        # 使用整個A4頁面作為可用空間（只留邊距，標籤會覆蓋在圖片上）
        available_width = self.A4_WIDTH - 2 * self.MARGIN
        available_height = self.A4_HEIGHT - 2 * self.MARGIN
        
        # 計算縮放比例
        scale_width = available_width / image_width
        scale_height = available_height / image_height
        
        # 選擇較小的縮放比例以確保圖片完全適合A4，但不放大小圖片
        scale = min(scale_width, scale_height, 1.0)
        
        # 計算最終尺寸
        final_width = image_width * scale
        final_height = image_height * scale
        
        # 判斷是否為橫向圖片（寬度大於高度）
        is_landscape = image_width > image_height
        
        return final_width, final_height, is_landscape
    
    def process_image(self, image_path: str) -> Tuple[Image.Image, bool]:
        """
        處理圖片：載入並判斷是否需要旋轉
        返回: (處理後的圖片, 是否已旋轉)
        """
        try:
            image = Image.open(image_path)
            
            # 轉換為RGB模式（確保相容性）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 判斷是否為橫向圖片
            is_landscape = image.width > image.height
            
            # 如果是橫向圖片，逆時針旋轉90度
            if is_landscape:
                image = image.rotate(90, expand=True)
                return image, True
            
            return image, False
            
        except Exception as e:
            raise Exception(f"處理圖片 {image_path} 時發生錯誤: {str(e)}")
    
    def split_text_units(self, text: str) -> List[str]:
        """
        將文字分割成顯示單元，連續數字視為一個單元
        例如："被上證15" → ["被", "上", "證", "15"]
        """
        units = []
        current_number = ""
        
        for char in text:
            if char.isdigit():
                current_number += char
            else:
                if current_number:
                    units.append(current_number)
                    current_number = ""
                units.append(char)
        
        # 處理結尾的數字
        if current_number:
            units.append(current_number)
        
        return units
    
    def add_text_label(self, pdf_canvas, label_text: str):
        """在PDF右上角添加文字標籤"""
        # 計算標籤位置（右上角）
        label_x = self.A4_WIDTH - self.LABEL_WIDTH - self.MARGIN
        label_y = self.A4_HEIGHT - self.LABEL_HEIGHT - self.MARGIN
        
        # 繪製白色背景填充
        pdf_canvas.setFillColor("white")
        pdf_canvas.rect(label_x, label_y, self.LABEL_WIDTH, self.LABEL_HEIGHT, fill=1, stroke=0)
        
        # 繪製黑色邊框
        pdf_canvas.setStrokeColor("black")
        pdf_canvas.setLineWidth(1)
        pdf_canvas.rect(label_x, label_y, self.LABEL_WIDTH, self.LABEL_HEIGHT, fill=0, stroke=1)
        
        # 註冊標楷體字型
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        try:
            # 在打包環境中尋找字型檔案
            font_name = "Helvetica"  # 預設字型
            
            # 嘗試多個可能的字型位置
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaiu.ttf"),  # Script's directory
                os.path.join(os.getcwd(), "kaiu.ttf"), # Working directory
            ]
            
            # 如果是打包環境，檢查資源目錄
            if getattr(sys, 'frozen', False):
                # PyInstaller 或 py2app 打包環境
                if hasattr(sys, '_MEIPASS'):
                    # PyInstaller
                    possible_paths.insert(0, os.path.join(sys._MEIPASS, "kaiu.ttf"))
                else:
                    # py2app - 檢查 Resources 目錄
                    app_path = os.path.dirname(sys.executable)
                    resources_path = os.path.join(os.path.dirname(app_path), "Resources")
                    possible_paths.insert(0, os.path.join(resources_path, "kaiu.ttf"))
            
            for font_path in possible_paths:
                if os.path.exists(font_path):
                    font_name = "KaiuFont"
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    print(f"成功載入標楷體字型: {font_path}")
                    break
            
            if font_name == "Helvetica":
                print("警告：找不到標楷體字型檔案，使用預設字型")
                
        except Exception as e:
            font_name = "Helvetica"
            print(f"載入字型時發生錯誤: {str(e)}，使用預設字型")
        
        # 設定文字樣式
        font_size = 16  # 增大字體大小
        pdf_canvas.setFont(font_name, font_size)
        pdf_canvas.setFillColor("black")  # 黑色文字
        
        # 實作中文直向文字排列（智能處理數字）
        text_units = self.split_text_units(label_text)
        unit_height = font_size * 1.1  # 單元間距
        total_text_height = len(text_units) * unit_height
        
        # 計算起始位置（讓文字在方塊中垂直居中）
        start_x = label_x + self.LABEL_WIDTH / 2
        # 垂直居中：方塊中心位置 + 文字總高度的一半
        text_center_y = label_y + self.LABEL_HEIGHT / 2
        start_y = text_center_y + total_text_height / 2
        
        # 逐單元繪製（由上到下）
        for i, unit in enumerate(text_units):
            unit_width = pdf_canvas.stringWidth(unit, font_name, font_size)
            unit_x = start_x - unit_width / 2  # 水平居中
            unit_y = start_y - i * unit_height - font_size  # 從上往下排列
            pdf_canvas.drawString(unit_x, unit_y, unit)
    
    def create_pdf_from_images(self, image_paths: List[str], output_path: str, label_text: str):
        """從圖片建立PDF"""
        pdf_canvas = canvas.Canvas(output_path, pagesize=A4)
        
        for i, image_path in enumerate(image_paths):
            if i > 0:  # 第一頁之後添加新頁面
                pdf_canvas.showPage()
            
            # 處理圖片
            processed_image, was_rotated = self.process_image(image_path)
            
            # 計算圖片在頁面上的位置和大小
            img_width, img_height, _ = self.get_optimal_image_size(
                processed_image.width, processed_image.height
            )
            
            # 計算置中位置（圖片在整個頁面中央，可被標籤方塊覆蓋）
            x = (self.A4_WIDTH - img_width) / 2
            y = (self.A4_HEIGHT - img_height) / 2
            
            # 將PIL圖片轉換為reportlab可用的格式
            temp_image_path = f"temp_image_{i}.jpg"
            processed_image.save(temp_image_path, "JPEG", quality=95)
            
            # 在PDF中繪製圖片
            pdf_canvas.drawImage(temp_image_path, x, y, width=img_width, height=img_height)
            
            # 只在第一頁添加文字標籤
            if i == 0:
                self.add_text_label(pdf_canvas, label_text)
            
            # 清理暫存檔案
            os.remove(temp_image_path)
        
        pdf_canvas.save()
    
    def process_existing_pdf(self, pdf_path: str, output_path: str, label_text: str):
        """處理既有的PDF檔案，保留原始內容並添加標籤"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from PyPDF2 import PdfReader, PdfWriter
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import io
            
            # 讀取原始PDF
            with open(pdf_path, 'rb') as input_file:
                pdf_reader = PdfReader(input_file)
                pdf_writer = PdfWriter()
                
                # 處理每一頁
                for page_num in range(len(pdf_reader.pages)):
                    original_page = pdf_reader.pages[page_num]
                    
                    # 創建一個新的PDF頁面來繪製標籤
                    packet = io.BytesIO()
                    overlay_canvas = canvas.Canvas(packet, pagesize=A4)
                    
                    # 只在第一頁添加標籤
                    if page_num == 0:
                        self.add_text_label(overlay_canvas, label_text)
                    overlay_canvas.save()
                    
                    # 移動到緩衝區開始
                    packet.seek(0)
                    overlay_pdf = PdfReader(packet)
                    
                    # 只有當有標籤時才疊加
                    if len(overlay_pdf.pages) > 0:
                        overlay_page = overlay_pdf.pages[0]
                        original_page.merge_page(overlay_page)
                    
                    pdf_writer.add_page(original_page)
                
                # 寫入輸出檔案
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                    
        except Exception as e:
            raise Exception(f"處理PDF檔案 {pdf_path} 時發生錯誤: {str(e)}")
    
    def generate_output_filename(self, input_paths: List[str], label_text: str) -> str:
        """自動生成輸出檔名"""
        # 取得第一個檔案的名稱（不含副檔名）
        first_file = Path(input_paths[0])
        base_name = first_file.stem
        
        # 清理標籤文字中的特殊字元，確保檔名安全
        safe_label = "".join(c for c in label_text if c.isalnum() or c in "()[]{}.-_")
        
        # 生成檔名：原檔名 + 標籤文字 + .pdf
        output_filename = f"{base_name}{safe_label}.pdf"
        
        # 確保輸出檔案在同一目錄
        output_path = first_file.parent / output_filename
        
        return str(output_path)
    
    def convert(self, input_paths: List[str], output_path: str, label_text: str):
        """主要轉換函數"""
        if not input_paths:
            raise ValueError("請提供至少一個輸入檔案")
        
        # 如果沒有指定輸出路徑，自動生成
        if not output_path:
            output_path = self.generate_output_filename(input_paths, label_text)
        
        # 分類檔案類型
        image_files = [f for f in input_paths if self.is_image_file(f)]
        pdf_files = [f for f in input_paths if self.is_pdf_file(f)]
        
        if not image_files and not pdf_files:
            raise ValueError("沒有找到支援的檔案格式")
        
        # 處理圖片檔案
        if image_files:
            self.create_pdf_from_images(image_files, output_path, label_text)
        
        # 處理PDF檔案（如果有的話）
        if pdf_files:
            if image_files:
                # 如果同時有圖片和PDF，需要合併處理
                print("警告：同時包含圖片和PDF檔案，目前只處理圖片檔案")
            else:
                # 只有PDF檔案
                self.process_existing_pdf(pdf_files[0], output_path, label_text)


def main():
    """主程式進入點"""
    parser = argparse.ArgumentParser(description='證據文件PDF轉換程式')
    parser.add_argument('files', nargs='+', help='要轉換的檔案路徑')
    parser.add_argument('-o', '--output', help='輸出PDF檔案路徑（可選，未指定時自動生成）')
    parser.add_argument('-l', '--label', required=True, help='標籤文字（如：原證1）')
    
    args = parser.parse_args()
    
    # 檢查輸入檔案是否存在
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"錯誤：檔案 {file_path} 不存在")
            sys.exit(1)
    
    # 建立轉換器並執行轉換
    converter = EvidencePDFConverter()
    
    try:
        # 如果沒有指定輸出檔案，傳入 None 讓程式自動生成
        output_path = args.output if args.output else None
        converter.convert(args.files, output_path, args.label)
        
        # 如果是自動生成檔名，要重新取得實際的輸出路徑來顯示
        if not args.output:
            actual_output = converter.generate_output_filename(args.files, args.label)
            print(f"轉換完成：{actual_output}")
        else:
            print(f"轉換完成：{args.output}")
    except Exception as e:
        print(f"轉換失敗：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()