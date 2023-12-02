import os
import re
import sys
from typing import Dict, List, Tuple, Union
from urllib.parse import urlparse

import pdfkit
import requests
import yaml
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger


# YAMLファイルの読み込み関数
def load_yaml_config(path):
    with open(path, 'r') as file:
        return yaml.safe_load(file)

# URLが許可リストにマッチするか確認する関数


def is_url_allowed(url, allowed_urls):
    return any(url.startswith(allowed_url) for allowed_url in allowed_urls)

# HTMLをPDFに変換する関数内で、出力パスのディレクトリが存在しない場合にディレクトリを作成する修正を追加します


def convert_html_to_pdf(html: str, output_path: str, options: Dict[str, Union[str, List[Tuple[str, str]]]]) -> None:

    print(output_path)
    # 出力ディレクトリが存在しない場合は作成する
    output_directory = os.path.dirname(output_path)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    try:
        pdfkit.from_string(html, output_path, options=options)
    except Exception:
        pass


# クローリングとPDF変換のメイン関数
def crawl_and_convert_to_pdf(start_url: str, allowed_urls: List[str], output_directory: str, pdf_option: Dict[str, Union[str, List[Tuple[str, str]]]]) -> None:
    # 訪問済みURLを追跡するためのセット
    visited_urls = set()

    # キューとしてリストを使用
    url_queue = [start_url]
    css_cache = {}
    counter = 1
    while url_queue:
        current_url = url_queue.pop(0)
        if current_url in visited_urls or not is_url_allowed(current_url, allowed_urls):
            continue

        parsed_url = urlparse(current_url)
        protocol = parsed_url.scheme
        host_name = parsed_url.netloc

        # HTMLを取得
        try:
            print(f"load url={current_url}")
            response = requests.get(current_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # CSS読み込みのタグからリンク先のURLを抽出
            css_links = [link.get('href') for link in soup.find_all(
                'link', href=True) if link.get('href').endswith(".css")]
            css = []
            for link in css_links:
                if link in css_cache:
                    css.append(css_cache[link])
                else:
                    try:
                        response = requests.get(
                            f"{protocol}://{host_name}{link}")
                        css_cache[link] = response.content.decode()
                        css.append(css_cache[link])
                    except Exception:
                        continue
            css_text = "\n".join(css)
        except Exception:
            continue

        # PDFに変換
        pdf_output_path = f"{output_directory}/{'%03d_' % counter}{urlparse(current_url).netloc}.pdf"
        counter = counter + 1
        convert_html_to_pdf(
            soup.prettify().replace(
                "</head>", f"<style>{css_text}</style></head>"),
            pdf_output_path,
            options=pdf_option)

        # 訪問済みに追加
        visited_urls.add(current_url)

        # ページ内のリンクを取得し、キューに追加
        for link in soup.find_all('a', href=True):
            url = f"{protocol}://{host_name}{link.get('href')}"
            url = url.split('#')[0]
            if url not in visited_urls and is_url_allowed(url, allowed_urls) and url not in url_queue:
                print(f"add queue url={url}")
                url_queue.append(url)


def merge_pdfs_in_directory(directory_path, output_path):
    merger = PdfMerger()

    # ファイル名でソートする処理を追加
    pdf_files = [f for f in os.listdir(directory_path) if f.endswith('.pdf')]
    pdf_files.sort()
    for item in pdf_files:
        merger.append(os.path.join(directory_path, item))

    merger.write(output_path)
    merger.close()


# メイン実行ブロック
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <YAML_CONFIG_PATH> <OUTPUT_FILE>")
        sys.exit(1)

    # コマンドライン引数からYAMLファイルパスと出力ディレクトリを取得
    yaml_path = sys.argv[1]
    output_file = sys.argv[2]

    # YAMLファイルの読み込み
    config = load_yaml_config(yaml_path)

    # クローリングとPDF変換を開始
    # crawl_and_convert_to_pdf(
    #     config['start_url'], 
    #     config['allowed_urls'], 
    #     "./work", 
    #     config['pdf_option'])

    # ファイルをまとめる
    merge_pdfs_in_directory('./work', output_file)
