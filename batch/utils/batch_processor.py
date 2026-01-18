"""
Batch Processor - 批量视频处理器
使用新的后端 API 进行批量处理
"""
import os
import sys
import time
import shutil
import requests
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

# 配置
API_BASE_URL = "http://127.0.0.1:8000/api"
SETTINGS_FILE = 'batch/tasks_setting.xlsx'
INPUT_FOLDER = 'batch/input'
OUTPUT_DIR = 'output'
SAVE_DIR = 'batch/output'
ERROR_OUTPUT_DIR = 'batch/output/ERROR'


class BatchProcessor:
    def __init__(self):
        self.api_base = API_BASE_URL
        
    def check_backend_running(self) -> bool:
        """检查后端服务是否运行"""
        try:
            resp = requests.get(f"{self.api_base}/processing/status", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def get_config(self) -> dict:
        """获取当前配置"""
        resp = requests.get(f"{self.api_base}/config")
        resp.raise_for_status()
        return resp.json()
    
    def update_config(self, config: dict) -> bool:
        """更新配置"""
        resp = requests.put(f"{self.api_base}/config", json=config)
        return resp.status_code == 200
    
    def upload_video(self, file_path: str) -> dict:
        """上传视频文件"""
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            resp = requests.post(f"{self.api_base}/video/upload", files=files)
            resp.raise_for_status()
            return resp.json()
    
    def start_processing(self, dubbing: bool = False) -> dict:
        """开始处理"""
        resp = requests.post(f"{self.api_base}/processing/start", json={"dubbing": dubbing})
        resp.raise_for_status()
        return resp.json()
    
    def get_processing_status(self) -> dict:
        """获取处理状态"""
        resp = requests.get(f"{self.api_base}/processing/status")
        resp.raise_for_status()
        return resp.json()
    
    def wait_for_completion(self, timeout: int = 3600) -> tuple:
        """
        等待处理完成
        返回: (success, current_stage, error_message)
        """
        start_time = time.time()
        last_stage = ""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Processing...", total=100)
            
            while time.time() - start_time < timeout:
                try:
                    status = self.get_processing_status()
                    current_stage = status.get('currentStage', '')
                    is_processing = status.get('isProcessing', False)
                    stage_progress = status.get('progress', 0)
                    error = status.get('error')
                    
                    # 更新进度显示
                    if current_stage != last_stage:
                        progress.update(task, description=f"[cyan]{current_stage}[/]")
                        last_stage = current_stage
                    
                    progress.update(task, completed=stage_progress)
                    
                    # 检查错误
                    if error:
                        return False, current_stage, error
                    
                    # 检查完成
                    if not is_processing and stage_progress >= 100:
                        progress.update(task, completed=100)
                        return True, current_stage, ""
                    
                    # 如果不在处理中且进度为0，可能是还没开始或已结束
                    if not is_processing and stage_progress == 0 and current_stage:
                        # 检查是否有输出文件
                        if os.path.exists('output/output_sub.mp4'):
                            return True, "completed", ""
                    
                    time.sleep(2)
                    
                except Exception as e:
                    console.print(f"[yellow]Status check error: {e}[/]")
                    time.sleep(5)
        
        return False, last_stage, "Timeout"
    
    def save_output(self, video_name: str, is_error: bool = False):
        """保存输出文件到对应目录"""
        base_name = os.path.splitext(video_name)[0]
        
        if is_error:
            target_dir = os.path.join(ERROR_OUTPUT_DIR, base_name)
        else:
            target_dir = os.path.join(SAVE_DIR, base_name)
        
        os.makedirs(target_dir, exist_ok=True)
        
        # 复制 output 目录内容
        if os.path.exists(OUTPUT_DIR):
            for item in os.listdir(OUTPUT_DIR):
                src = os.path.join(OUTPUT_DIR, item)
                dst = os.path.join(target_dir, item)
                
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
        
        console.print(f"[green]Output saved to: {target_dir}[/]")
    
    def restore_from_error(self, video_name: str) -> bool:
        """从 ERROR 目录恢复文件以重试"""
        base_name = os.path.splitext(video_name)[0]
        error_folder = os.path.join(ERROR_OUTPUT_DIR, base_name)
        
        if not os.path.exists(error_folder):
            console.print(f"[yellow]Error folder not found: {error_folder}[/]")
            return False
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        for item in os.listdir(error_folder):
            src = os.path.join(error_folder, item)
            dst = os.path.join(OUTPUT_DIR, item)
            
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.copy2(src, dst)
        
        console.print(f"[green]Restored files from ERROR folder for {video_name}[/]")
        return True
    
    def clear_output(self):
        """清空 output 目录"""
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)


def check_settings() -> bool:
    """检查配置文件和输入文件"""
    os.makedirs(INPUT_FOLDER, exist_ok=True)
    
    if not os.path.exists(SETTINGS_FILE):
        console.print(Panel(
            f"Settings file not found: {SETTINGS_FILE}\n"
            "Please create a tasks_setting.xlsx with columns:\n"
            "Video File | Source Language | Target Language | Dubbing | Status",
            title="[bold red]Error",
            expand=False
        ))
        return False
    
    df = pd.read_excel(SETTINGS_FILE)
    input_files = set(os.listdir(INPUT_FOLDER))
    excel_files = set(df['Video File'].tolist())
    files_not_in_excel = input_files - excel_files
    
    all_passed = True
    
    if files_not_in_excel:
        console.print(Panel(
            "\n".join([f"- {file}" for file in files_not_in_excel]),
            title="[bold yellow]Warning: Files in input folder not in Excel",
            expand=False
        ))
    
    for index, row in df.iterrows():
        video_file = row['Video File']
        dubbing = row['Dubbing']
        
        # 检查视频文件
        if video_file.startswith('http'):
            pass  # URL 暂不支持批处理
        elif not os.path.isfile(os.path.join(INPUT_FOLDER, video_file)):
            console.print(Panel(
                f"Video file not found: {video_file}",
                title=f"[bold red]Error in row {index + 2}",
                expand=False
            ))
            all_passed = False
        
        # 检查 dubbing 值
        if not pd.isna(dubbing) and int(dubbing) not in [0, 1]:
            console.print(Panel(
                f"Invalid dubbing value: {dubbing}",
                title=f"[bold red]Error in row {index + 2}",
                expand=False
            ))
            all_passed = False
    
    if all_passed:
        task_count = len(df[df['Status'].isna() | df['Status'].str.contains('Error', na=False)])
        console.print(Panel(
            f"Total tasks to process: {task_count}",
            title="[bold green]Settings Check Passed",
            expand=False
        ))
    
    return all_passed


def process_batch():
    """主批处理函数"""
    processor = BatchProcessor()
    
    # 检查后端服务
    console.print("[cyan]Checking backend service...[/]")
    if not processor.check_backend_running():
        console.print(Panel(
            "Backend service is not running!\n"
            "Please start the backend first:\n"
            "  ./start_backend.bat  (Windows)\n"
            "  ./start_backend.ps1  (PowerShell)",
            title="[bold red]Error",
            expand=False
        ))
        return
    console.print("[green]✓ Backend service is running[/]\n")
    
    # 检查配置
    if not check_settings():
        return
    
    # 读取任务
    df = pd.read_excel(SETTINGS_FILE)
    
    for index, row in df.iterrows():
        status = row['Status']
        
        # 跳过已完成的任务
        if not pd.isna(status) and status == 'Done':
            console.print(f"[dim]Skipping completed: {row['Video File']}[/]")
            continue
        
        # 跳过非错误状态的任务
        if not pd.isna(status) and 'Error' not in str(status):
            continue
        
        video_file = row['Video File']
        source_lang = row['Source Language'] if not pd.isna(row['Source Language']) else None
        target_lang = row['Target Language'] if not pd.isna(row['Target Language']) else None
        dubbing = int(row['Dubbing']) if not pd.isna(row['Dubbing']) else 0
        is_retry = not pd.isna(status) and 'Error' in str(status)
        
        total_tasks = len(df)
        
        # 显示任务信息
        if is_retry:
            console.print(Panel(
                f"Retrying: {video_file}\nTask {index + 1}/{total_tasks}",
                title="[bold yellow]Retry Task",
                expand=False
            ))
            processor.restore_from_error(video_file)
        else:
            console.print(Panel(
                f"Processing: {video_file}\nTask {index + 1}/{total_tasks}",
                title="[bold blue]Current Task",
                expand=False
            ))
            processor.clear_output()
        
        try:
            # 更新配置（语言设置）
            if source_lang or target_lang:
                config = processor.get_config()
                if source_lang:
                    config['sourceLanguage'] = source_lang
                if target_lang:
                    config['targetLanguage'] = target_lang
                processor.update_config(config)
            
            # 上传视频（如果不是重试）
            if not is_retry:
                input_path = os.path.join(INPUT_FOLDER, video_file)
                console.print(f"[cyan]Uploading video: {video_file}[/]")
                processor.upload_video(input_path)
            
            # 开始处理
            console.print(f"[cyan]Starting processing (dubbing={dubbing})...[/]")
            processor.start_processing(dubbing=bool(dubbing))
            
            # 等待完成
            success, stage, error = processor.wait_for_completion()
            
            if success:
                status_msg = "Done"
                processor.save_output(video_file, is_error=False)
                console.print(Panel(
                    f"[bold green]✓ Completed: {video_file}[/]",
                    border_style="green"
                ))
            else:
                status_msg = f"Error: {stage} - {error}"
                processor.save_output(video_file, is_error=True)
                console.print(Panel(
                    f"[bold red]✗ Failed: {video_file}\n{error}[/]",
                    border_style="red"
                ))
        
        except Exception as e:
            status_msg = f"Error: Unhandled - {str(e)}"
            processor.save_output(video_file, is_error=True)
            console.print(f"[bold red]Error processing {video_file}: {e}[/]")
        
        # 更新 Excel 状态
        df.at[index, 'Status'] = status_msg
        df.to_excel(SETTINGS_FILE, index=False)
        
        # 短暂等待
        time.sleep(2)
    
    console.print(Panel(
        "All tasks processed!\nCheck results in `batch/output`",
        title="[bold green]Batch Processing Complete",
        expand=False
    ))


if __name__ == "__main__":
    process_batch()
