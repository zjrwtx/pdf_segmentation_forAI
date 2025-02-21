import os
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import gradio as gr

def get_pdf_size(pdf_writer):
    """获取当前PdfWriter对象的内容大小（以字节为单位）"""
    buffer = BytesIO()
    pdf_writer.write(buffer)
    return buffer.tell()

def split_pdf_by_pages(input_pdf_path, output_folder, split_pages):
    """按分页数分割PDF"""
    # 创建输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 读取PDF文件
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)

    # 检查用户输入的分页数是否有效
    if any(page > total_pages or page < 1 for page in split_pages):
        return f"错误：分页数超出PDF总页数范围（总页数：{total_pages}）。"

    # 对分页数进行排序并去重
    split_pages = sorted(set(split_pages))

    # 切割PDF
    start_page = 0
    result_files = []
    for i, split_page in enumerate(split_pages):
        writer = PdfWriter()
        end_page = split_page - 1  # PyPDF2的页码从0开始

        # 添加从 start_page 到 end_page 的页面
        for page_num in range(start_page, end_page + 1):
            writer.add_page(reader.pages[page_num])

        # 保存切割后的PDF文件
        output_pdf_path = os.path.join(output_folder, f"part_{i+1}.pdf")
        with open(output_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)

        result_files.append(output_pdf_path)
        start_page = end_page + 1

    # 处理最后一组页面
    if start_page < total_pages:
        writer = PdfWriter()
        for page_num in range(start_page, total_pages):
            writer.add_page(reader.pages[page_num])

        output_pdf_path = os.path.join(output_folder, f"part_{len(split_pages) + 1}.pdf")
        with open(output_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)

        result_files.append(output_pdf_path)

    return result_files

def split_pdf_by_size(input_pdf_path, output_folder, max_size_mb):
    """按文件大小分割PDF"""
    # 创建输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 读取PDF文件
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)

    # 初始化变量
    writer = PdfWriter()
    current_part = 1
    max_size_bytes = max_size_mb * 1024 * 1024  # 将MB转换为字节
    result_files = []

    # 逐页处理
    for page_num in range(total_pages):
        # 添加当前页
        writer.add_page(reader.pages[page_num])

        # 检查当前文件大小
        current_size = get_pdf_size(writer)
        if current_size >= max_size_bytes:
            # 如果超过最大大小，保存当前部分
            output_pdf_path = os.path.join(output_folder, f"part_{current_part}.pdf")
            with open(output_pdf_path, "wb") as output_pdf:
                writer.write(output_pdf)
            result_files.append(output_pdf_path)

            # 重置writer并增加部分计数
            writer = PdfWriter()
            current_part += 1

    # 保存最后一部分（如果有剩余页面）
    if len(writer.pages) > 0:
        output_pdf_path = os.path.join(output_folder, f"part_{current_part}.pdf")
        with open(output_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)
        result_files.append(output_pdf_path)

    return result_files

def process_pdf(input_pdf, mode, split_pages=None, max_size_mb=None):
    """处理PDF文件"""
    output_folder = "output_parts"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if mode == "按分页数分割":
        if not split_pages:
            return "错误：请输入分页数。"
        split_pages = [int(page) for page in split_pages.split(",")]
        result_files = split_pdf_by_pages(input_pdf, output_folder, split_pages)
    elif mode == "按文件大小分割":
        if not max_size_mb:
            return "错误：请输入最大文件大小。"
        result_files = split_pdf_by_size(input_pdf, output_folder, float(max_size_mb))
    else:
        return "错误：无效的模式。"

    if isinstance(result_files, str):  # 如果返回的是错误信息
        return result_files

    # 返回所有生成的文件
    return result_files

# Gradio 界面
with gr.Blocks() as demo:
    gr.Markdown("# PDF 分割工具")
    with gr.Row():
        input_pdf = gr.File(label="上传PDF文件", type="filepath")
        mode = gr.Radio(choices=["按分页数分割", "按文件大小分割"], label="选择分割模式")
    with gr.Row():
        split_pages = gr.Textbox(label="分页数（例如：3,5,10）", visible=True)
        max_size_mb = gr.Number(label="每部分的最大大小（MB）", visible=False)
    with gr.Row():
        output_files = gr.Files(label="分割后的文件")
    with gr.Row():
        submit_btn = gr.Button("开始分割")
        download_all_btn = gr.Button("批量下载")

    # 动态显示/隐藏输入框
    def toggle_inputs(mode):
        if mode == "按分页数分割":
            return gr.Textbox(visible=True), gr.Number(visible=False)
        else:
            return gr.Textbox(visible=False), gr.Number(visible=True)

    # 批量下载功能
    def download_all_files(file_list):
        if not file_list:
            return None
        # 创建一个临时zip文件
        import tempfile
        import zipfile
        import shutil

        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zf:
                for file_path in file_list:
                    # 获取文件名
                    file_name = os.path.basename(file_path)
                    # 将文件添加到zip中
                    zf.write(file_path, file_name)
            return temp_zip.name

    mode.change(toggle_inputs, inputs=mode, outputs=[split_pages, max_size_mb])

    # 绑定处理函数
    submit_btn.click(
        process_pdf,
        inputs=[input_pdf, mode, split_pages, max_size_mb],
        outputs=output_files
    )

    # 绑定批量下载函数
    download_all_btn.click(
        download_all_files,
        inputs=[output_files],
        outputs=gr.File(label="下载所有文件")
    )

    theme=gr.themes.Soft()

# 启动应用
demo.launch()
