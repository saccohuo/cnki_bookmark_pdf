# -*- coding: utf-8
#
# 思路：
# 1. 设置 pdf 文件名，网页地址；Done
# 2. 对 CNKI 的网址处理，获取“分章下载”按钮对应的 url，即得到书签页的网页地址；Done
# 3. 利用爬虫获取书签页的所有文本（包括缩进信息）；Done
# 4. 处理获取的书签文本，进行二次处理，参考“知网书签.bas”；Done
# 5. 利用 pypdf2 和 pdfbookmarker 把处理之后的书签文本（含缩进）挂到 pdf 文件中。Done
# 6. 现在如果只有第一个参数的话，是找到最近修改的文件，然后判断它是不是 pdf 的，后续可能需要改成找到最近的 pdf 文件，当然还要设定一定数量范围内，比如10个文件以内。Done
#
# TODO
# 1. 可以借鉴油猴脚本直接获取 pdf 下载地址，并下载（curl or wget or aria2）。已下载到 “cnki_pdf_href_gen.js” 中。还是很有难度的。暂时用的 requests。
# 2. 封装一下，就不需要安装 python 和这么多 package 的。暂时可以安装 anaconda（建议） 或 Python 原版（原版需要安装很多 package）。
# 3. 解决参数中字符串形式的 Windows 路径最后的反斜杠被作为转义字符的问题。如“python cnki_bookmark_pdf.py "G:\IDMDownload\test_cnki\"”会导致最后的双引号被转义，出现识别错误。


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

def getRecentPdf(base_dir, num):
    allfile = os.listdir(base_dir)
    allfile.sort(key=lambda fn: os.path.getmtime(os.path.join(base_dir, fn)) if not os.path.isdir(os.path.join(base_dir, fn)) else 0, reverse=True)
    # recentfile = allfile[-1]
    for ind,tpfile in enumerate(allfile):
        if os.path.splitext(tpfile)[1]=='.pdf':
            return tpfile
        if ind==num-1:
            return None
    return -1

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

def getPdfDownloadUrl(url):
    try:
        html = urlopen(url)
    except HTTPError as e:
        return None
    try:
        # bsObj = BeautifulSoup(html.read(), "html.parser")
        bsObj = BeautifulSoup(html, "lxml")
        # match_list = bsObj.find_all('a', string="CAJ下载")
        match_list = bsObj.find_all('a', string="整本下载")
        # print(len(match_list))
        match_link = match_list[0].attrs["href"]
        match_link = match_link.replace("nhdown", "pdfdown")
        # print(match_link)
    except AttributeError as e:
        return None
    return match_link

def cnki_get_bookmark(bookmarkfile, paperurl):
    bookmarkurl = getBookmarkUrl(paperurl)
    if bookmarkurl == None:
        print("Bookmark page on CNKI could not be found.")
        return -1

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
    return 0


def cnki_add_bookmark(pdffullpath=None, paperurl=None):
    defaultpath = 'G:/IDMDownload/'
    recentnum = 10
    # defaultpath = os.getcwd()
    if pdffullpath == None or pdffullpath == '':
        pdfpath = defaultpath
        pdffilename = getRecentPdf(pdfpath, recentnum)
    elif os.path.isdir(pdffullpath):
        pdfpath = pdffullpath
        pdffilename = getRecentPdf(pdfpath, recentnum)
    else:
        curpdfpath = os.path.dirname(pdffullpath)
        curpdffilename = os.path.basename(pdffullpath)
        curpdffileext = os.path.splitext(curpdffilename)[1]
        if curpdfpath != '' and os.path.isdir(curpdfpath) == False:
            print("The specified path doesn't exist.")
            return -1
        else:
            if curpdfpath != '' and os.path.isdir(curpdfpath) == True:
                pdfpath = curpdfpath
            else:
                pdfpath = defaultpath
            if curpdffilename == '':
                pdffilename = getRecentPdf(pdfpath, recentnum)
            else:
                pdffilename = curpdffilename

    if pdffilename == None:
        print("The recent downloaded file is not pdf.")
        return -1
    # print(pdfpath)
    # print(pdffilename)
    pdffilename_split = os.path.splitext(pdffilename)
    pdffilename_out = pdffilename_split[0]+'_out'+pdffilename_split[1]
    pdffile = os.path.join(pdfpath, pdffilename)
    pdffile_out = os.path.join(pdfpath, pdffilename_out)
    if os.path.isfile(pdffile) == False:
        print("The specified file doesn't exist.")
        return -1
    if paperurl == None:
        paperurl = getCopyText().decode('utf-8')
    if urlmatch(paperurl, rule='IRI') == None:
        print("The text in clipboard is not a valid url.")
        return -1
    bookmarkfilename = pdffilename_split[0]+'_bookmark.txt'
    bookmarkfile = os.path.join(pdfpath, bookmarkfilename)

    get_bookmark_flag = cnki_get_bookmark(bookmarkfile, paperurl)
    if get_bookmark_flag==-1:
        return -1
    add_bookmarks.run_script(pdffile, bookmarkfile, pdffile_out)
    if os.path.isfile(bookmarkfile):
        os.remove(bookmarkfile)
    return 0

if __name__ == '__main__':
    import sys
    # print(len(sys.argv))
    if len(sys.argv) not in (1, 2, 3):
        # sys.stderr.write(__doc__)
        sys.exit("Wrong number of arguments!")
    cnki_add_bookmark(*sys.argv[1:])
