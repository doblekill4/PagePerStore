from playwright.sync_api import sync_playwright
import time
import os
import threading
import win32clipboard
import argparse
import sys

# ===================== 配置 =====================
WPS_USER_DATA_DIR = "./wps_profile"
WPS_URL = "https://www.kdocs.cn/l/ceIalhfmfGZ6"
SHEET_NAME_MAIN = "服务一店一页"


def set_clipboard(text: str, put_html: bool = True):
    """Set both plain-text and HTML table representation to the Windows clipboard.

    If put_html is True and the text looks like TSV (tabs/newlines), an HTML
    table will be constructed and put on the clipboard using the registered
    'HTML Format'. This helps web editors (browser-based sheets) paste the
    data as table cells and preserves intra-cell newlines as <br/>.
    """
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()

        try:
            win_text = None
            if put_html and isinstance(text, str):
                try:
                    import csv as _csv, io as _io
                    buf = _io.StringIO(text)
                    rdr = _csv.reader(buf, delimiter='\t', quoting=_csv.QUOTE_MINIMAL)
                    out_lines = []
                    for rec in rdr:
                        safe_fields = []
                        for f in rec:
                            if f is None:
                                ff = ''
                            else:
                                ff = str(f).replace('\r', '').replace('\n', ' ')
                            safe_fields.append(ff)
                        out_lines.append('\t'.join(safe_fields))
                    win_text = '\r\n'.join(out_lines)
                except Exception:
                    win_text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
            else:
                win_text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')

            try:
                win32clipboard.SetClipboardText(win_text, win32clipboard.CF_UNICODETEXT)
            except Exception:
                try:
                    win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, win_text)
                except Exception:
                    pass
        except Exception:
            pass

        if put_html and isinstance(text, str) and ('\t' in text or '\n' in text):
            try:
                import html as _html, csv as _csv, io as _io, glob

                def _find_latest_client_table_header():
                    here = os.path.abspath(os.path.dirname(__file__))
                    pattern = os.path.join(here, '临时_clip_*_html.html')
                    files = glob.glob(pattern)
                    if not files:
                        return None
                    files.sort()
                    latest = files[-1]
                    try:
                        with open(latest, 'r', encoding='utf-8', errors='replace') as cf:
                            data = cf.read()
                        sf = data.find('<!--StartFragment-->')
                        ef = data.find('<!--EndFragment-->')
                        fragment = data[sf+len('<!--StartFragment-->'):ef] if sf!=-1 and ef!=-1 else data
                        tstart = fragment.find('<table')
                        if tstart == -1:
                            return None
                        trpos = fragment.find('<tr', tstart)
                        if trpos == -1:
                            return None
                        header_html = fragment[tstart:trpos]
                        return header_html
                    except Exception:
                        return None

                rows = []
                try:
                    buf = _io.StringIO(text)
                    rdr = _csv.reader(buf, delimiter='\t', quoting=_csv.QUOTE_MINIMAL)
                    for rec in rdr:
                        if not rec:
                            continue
                        esc_cells = []
                        for c in rec:
                            raw = '' if c is None else str(c)
                            raw = raw.replace('\r', '')
                            parts = raw.split('\n')
                            escaped_parts = [_html.escape(p) for p in parts]
                            cell_html = '<br>'.join(escaped_parts) if len(escaped_parts) > 1 else (escaped_parts[0] if escaped_parts else '')
                            esc_cells.append(cell_html)
                        rows.append(esc_cells)
                except Exception:
                    for line in text.split('\n'):
                        if line == '':
                            continue
                        cells = line.split('\t')
                        esc_cells = []
                        for c in cells:
                            if len(c) >= 2 and c[0] == '"' and c[-1] == '"':
                                raw = c[1:-1]
                            else:
                                raw = c
                            parts = raw.replace('\r', '').split('\n')
                            escaped_parts = [_html.escape(p) for p in parts]
                            if len(escaped_parts) > 1:
                                cell_html = '<br>'.join(escaped_parts)
                            else:
                                cell_html = escaped_parts[0] if escaped_parts else ''
                            esc_cells.append(cell_html)
                        rows.append(esc_cells)

                try:
                    client_header = _find_latest_client_table_header()
                except Exception:
                    client_header = None

                if client_header:
                    frag_lines = []
                    for r in rows:
                        row_cells = []
                        for c in r:
                            row_cells.append(f'<td>{c}</td>')
                        frag_lines.append('<tr>' + ''.join(row_cells) + '</tr>')
                    table_html = client_header + ''.join(frag_lines) + '</table>'
                    fragment = table_html
                else:
                    frag_lines = ['<table>']
                    for r in rows:
                        frag_lines.append('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>')
                    frag_lines.append('</table>')
                    fragment = ''.join(frag_lines)

                try:
                    html_bytes = _build_cf_html_excel_like(fragment)
                    if html_bytes:
                        try:
                            fmt = win32clipboard.RegisterClipboardFormat('HTML Format')
                            win32clipboard.SetClipboardData(fmt, html_bytes)
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception:
                pass
    except Exception:
        pass
    finally:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass

def _build_cf_html_excel_like(fragment: str) -> bytes:
    head = (
        '<html xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">'
        '<head><meta http-equiv=Content-Type content="text/html; charset=utf-8">'
        '<meta name=Generator content="Microsoft Excel">'
        '<style>br{mso-data-placement:same-cell;} td{white-space:normal;}</style>'
        '</head>'
    )
    body_open = '<body>'
    body_close = '</body></html>'

    full_html = '<!DOCTYPE html>' + head + body_open + '<!--StartFragment-->' + fragment + '<!--EndFragment-->' + body_close
    full_bytes = full_html.encode('utf-8')

    prefix = f"Version:0.9\r\n"
    start_html = len(prefix.encode('utf-8'))
    end_html_val = start_html + len(full_bytes)
    frag_start = full_html.find('<!--StartFragment-->') + len('<!--StartFragment-->')
    frag_end = full_html.find('<!--EndFragment-->')
    start_fragment_val = start_html + len(full_html[:frag_start].encode('utf-8'))
    end_fragment_val = start_html + len(full_html[:frag_end].encode('utf-8'))
    header = (
        f"Version:0.9\r\nStartHTML:{start_html:08d}\r\nEndHTML:{end_html_val:08d}\r\n"
        f"StartFragment:{start_fragment_val:08d}\r\nEndFragment:{end_fragment_val:08d}\r\n"
    )
    return header.encode('utf-8') + full_bytes


def wps_first_login():
    if os.path.exists(WPS_USER_DATA_DIR):
        print("✅ 已存在登录状态，跳过登录")
        return True

    print("👉 首次登录：打开浏览器，请手动登录金山文档...")
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(user_data_dir=WPS_USER_DATA_DIR, headless=False)
            page = context.new_page()
            page.goto(WPS_URL)
            page.get_by_text(SHEET_NAME_MAIN).wait_for(timeout=120000)
            context.close()
        print("✅ 登录成功，状态已保存")
        return True
    except Exception as e:
        print(f"⚠️ 登录流程：{e}")
        return True


def wps_append_data(data_list, is_today_order=True, use_legacy_paste=True, paste_as_values=True):
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=WPS_USER_DATA_DIR,
                headless=False,
                slow_mo=300
            )

            page = context.new_page()
            print("✅ 打开表格...")
            page.goto(WPS_URL)
            page.wait_for_load_state("networkidle")

            # 切换工作表
            print("✅ 切换到【服务一店一页】")
            page.get_by_text(SHEET_NAME_MAIN).wait_for(timeout=15000)
            page.get_by_text(SHEET_NAME_MAIN).click()
            time.sleep(2)

            # ============================
            # 【极简定位】你验证过能跑的！
            # 无选择器 · 无等待 · 不超时
            # ============================
            print("📌 定位到最后一行空行...")
            page.mouse.click(500, 300)
            page.keyboard.press("Control+Home")
            page.keyboard.press("Control+ArrowDown")
            page.keyboard.press("ArrowDown")
            print("✅ 定位完成！")

            # 生成TSV
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output, delimiter='\t', lineterminator='\n')
            for row in data_list:
                values = [str(row.get(k, '')).replace('\n', ' ').replace('\r', '') for k in row.keys()]
                writer.writerow(values)
            tsv = output.getvalue()

            # 粘贴
            set_clipboard(tsv)
            page.keyboard.press("Control+v")
            print("✅ 数据粘贴完成！")

            time.sleep(2)
            context.close()
            return True

    except Exception as e:
        print(f"❌ 写入失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def start_wps_keep_alive():
    threading.Thread(target=wps_first_login, daemon=True).start()


def get_clipboard_text() -> str:
    try:
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT) or ''
        win32clipboard.CloseClipboard()
        return data
    except Exception:
        return ''


def cli_main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    tsv = get_clipboard_text()
    wps_append_data([])

if __name__ == '__main__':
    cli_main()
