# -*- coding: utf-8
# 思路：
# 1. 设置 pdf 文件名，网页地址；Done
# 2. 对 CNKI 的网址处理，获取“分章下载”按钮对应的 url，即得到书签页的网页地址；Done
# 3. 利用爬虫获取书签页的所有文本（包括缩进信息）；Done
# 4. 处理获取的书签文本，进行二次处理，参考“知网书签.bas”；Done
# 5. 利用 pypdf2 和 pdfbookmarker 把处理之后的书签文本（含缩进）挂到 pdf 文件中。Done
# 0. 可以借鉴油猴脚本直接获取 pdf 下载地址，并下载（curl or wget or aira2）。已下载到 “cnki_pdf_href_gen.js” 中。TODO



import os
import re
from urllib.request import urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup
from lxml import etree
import win32clipboard as wc
import win32con
from rfc3987 import match as urlmatch
import add_bookmarks

__all__ = [
    'cnki_pdf_add_bookmark'
]

__author__ = 'SaccoHuo'
__version__ = '0.01'


def getCopyText():
    wc.OpenClipboard()
    copy_text = wc.GetClipboardData(win32con.CF_TEXT)
    wc.CloseClipboard()
    return copy_text

def getRecentUpdateFile(base_dir):
    allfile = os.listdir(base_dir)
    allfile.sort(key=lambda fn: os.path.getmtime(base_dir+fn) if not os.path.isdir(base_dir+fn) else 0)
    recentfile = allfile[-1]
    if os.path.splitext(recentfile)[1]=='.pdf':
        return recentfile
    else:
        return None

def getBookmarkUrl(url):
    try:
        html = urlopen(url)
    except HTTPError as e:
        return None
    try:
        # bsObj = BeautifulSoup(html.read(), "html.parser")
        bsObj = BeautifulSoup(html, "lxml")
        match_list = bsObj.find_all('a', string="分章下载")
        # print(len(match_list))
        match_link = match_list[0].attrs["href"]
        # print(match_link)
    except AttributeError as e:
        return None
    return match_link

def cnki_add_bookmark(pdfpath=None, pdffilename=None, paperurl=None):
    if pdfpath == None:
        pdfpath = 'G:/IDMDownload/'
    if pdffilename == None:
        pdffilename = getRecentUpdateFile(pdfpath)
    if pdffilename == None:
        print("The recent downloaded file is not pdf.")
        return
    pdffilename_split = os.path.splitext(pdffilename)
    pdffilename_out = pdffilename_split[0]+'_out'+pdffilename_split[1]
    pdffile = os.path.join(pdfpath, pdffilename)
    pdffile_out = os.path.join(pdfpath, pdffilename_out)
    if paperurl == None:
        paperurl = getCopyText().decode('utf-8')
    if urlmatch(paperurl, rule='IRI') == None:
        print("The text in clipboard is not a valid url.")
        return
    bookmarkfilename = pdffilename_split[0]+'_bookmark.txt'
    bookmarkfile = os.path.join(pdfpath, bookmarkfilename)

    bookmarkurl = getBookmarkUrl(paperurl)
    if bookmarkurl == None:
        print("Bookmark url could not be found.")
        return

    html = urlopen(bookmarkurl).read()
    soup = BeautifulSoup(html, 'html.parser')

    [script.extract() for script in soup.findAll('script')]
    [style.extract() for style in soup.findAll('style')]
    # print(type(str(soup)))
    reg1 = re.compile("<[^>]*>")
    # content = reg1.sub('',soup.prettify())
    content = reg1.sub('', str(soup))
    # print(content)

    # 去除空白行（除\r行）
    content = re.sub(r'^\n|\n+(?=\n)|\n$', r'', content)
    # content = re.sub(r'^\r\n$', r'', content)
    # 去除GBK编码文件的换行带来的\r
    content = re.sub(r'\n\r', r'', content)
    # 把标题与页码放在一行，并只保留第一个页码
    content = re.sub(r'\n(\d+)-?\d*', r'|\1', content)
    # 把四个空格替换为一个加号或者\t
    content = re.sub(r' {4}', r'+', content)
    # 每一列前面加个加号
    content = re.sub(r'\n(.*)', r'\n+\1', content)
    # 目录字符串前后加上双引号
    content = re.sub(r'(\++)(.*)(\|\d+)', r'\1"\2"\3', content)
    # 删除第一行的文章目录名
    content = re.sub(r'  .*\n', r'', content, 1)

    # ct = re.subn(r'\n(.*)', r'\n+\1', content)
    # content = ct[0]
    # print(ct[1])
    fp = open(bookmarkfile,'w',encoding='utf-8')
    # print(fp.encoding)
    fp.write(content)
    fp.close()
    add_bookmarks.run_script(pdffile, bookmarkfile, pdffile_out)
    return

if __name__ == '__main__':
    import sys
    # print(len(sys.argv))
    if len(sys.argv) not in (1, 2, 3, 4):
        # sys.stderr.write(__doc__)
        sys.exit("Wrong number of arguments!")
    cnki_add_bookmark(*sys.argv[1:])
