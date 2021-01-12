import re

import requests
from lxml import etree
from colorama import Fore, Style
from prettytable import PrettyTable as pt


class retry(object):
    def __init__(self, count=5):
        pass

    def __call__(self, _func):
        def _wrapper(*args, **kwargs):
            for _ in range(5):
                try:
                    result = _func(*args, **kwargs)
                except Exception as e:
                    print(f'[!] {put_color(e, "gray")}')
                else:
                    return result

        return _wrapper


def put_color(string, color, bold=True):
    '''
    give me some color to see :P
    '''

    if color == 'gray':
        COLOR = Style.DIM + Fore.WHITE
    else:
        COLOR = getattr(Fore, color.upper(), Fore.WHITE)

    return f'{Style.BRIGHT if bold else ""}{COLOR}{str(string)}{Style.RESET_ALL}'


@retry()
def send(url, method='get', headers=None, params=None, data=None, json=False):
    response = getattr(requests, method)(
        url,
        params=params,
        data=data,
        headers=headers,
        timeout=(10, 10)
    )
    if json:
        result = response.json()
    else:
        result = response.text

    return result


def show(fund_name, fund_code, data, today_increase=0, is_etf=False):
    fund_name = put_color(fund_name, "blue")
    if is_etf:
        print(f'\n[{fund_code}] {fund_name}')
        print(f'  [-] {put_color("此为 ETF 基金，无法估算 PE", "gray")}')
        return

    tb = pt(border=False, header=False)
    tb.field_names = ["股票名", "比例", "PE", "今日涨幅"]
    tb.align["股票名"] = "l"
    tb.align["今日涨幅"] = "l"
    inc_color = 'red'
    tip = '↑'

    if today_increase < 0:
        inc_color = 'green'
        tip = '↓'

    print(f'\n[{fund_code}] {fund_name} {put_color(f"{tip} {today_increase}%", inc_color)}')

    cal_pe_rate = 0
    for d in data[:5]:
        inc_color = 'red'
        tip = '↑'
        if d[3] < 0:
            inc_color = 'green'
            tip = '↓'

        tb.add_row([f' [-] {d[0]}', d[1], d[2], put_color(f'{tip} {d[3]}%', inc_color, False)])
        cal_pe_rate += float(d[1][:-1])/100*float(d[2])

    print(tb)
    cal_pe_rate = round(cal_pe_rate, 2)
    color = 'cyan'
    if cal_pe_rate > 50:
        color = 'yellow'

    print(f'  [-] PE: {put_color(cal_pe_rate, color)}')


@retry()
def get_fund_info(fund_code):
    today_increase = round(float(re.findall(
        '<span id="fund_gszf" .+>(.+)%</span>',
        send(f'http://fundf10.eastmoney.com/ccmx_{fund_code}.html')
    )[0]), 2)

    params = {
        'type': 'jjcc',
        'code': fund_code,
        'topline': '1000',
        'year': '2020',
        'month': '9',
        'rt': '0.07460008078625502',
    }
    html = send(
        'http://fundf10.eastmoney.com/FundArchivesDatas.aspx',
        params=params,
        headers={
            'Referer': 'http://fundf10.eastmoney.com/ccmx_161725.html',
        }
    )
    weird = '<th>最新价</th>' not in html
    html = etree.HTML(re.findall('var apidata={ content:"(.+)",arryear', html)[0])

    fund_name = html.xpath('/html/body/div[1]/div/h4/label[1]/a/text()')[0]
    if 'etf' in fund_name.lower():
        show(fund_name, fund_code, [], is_etf=True)
        return

    if weird:
        secids = []
        root = '/html/body/div[1]/div/table/tbody/tr'
        for i in range(len(html.xpath(root))):
            stock_code = html.xpath(f'{root}[{i+1}]/td[2]/a/text()')[0]
            if stock_code.startswith('0'):
                stock_code = '0.'+stock_code
            else:
                stock_code = '1.'+stock_code

            secids.append(stock_code)

        secids = ','.join(secids)

    else:
        secids = html.xpath('//*[@id="gpdmList"]/text()')[0]

    params = {
        'fields': 'f3,f9,f14',
        'secids': secids,
        'fltt': '2',
        'invt': '2',
    }

    data = send(
        'https://push2.eastmoney.com/api/qt/ulist.np/get',
        params=params,
        json=True
    )

    if not data['data']:
        print(data)

    result = []
    stocks = data['data']['diff']
    loc = 5 if weird else 7
    for i, stock in enumerate(stocks):
        precent = html.xpath(f'/html/body/div[1]/div/table/tbody/tr[{i+1}]/td[{loc}]/text()')[0]
        pe_rate = float(stock['f9'])
        name = stock['f14'].replace(' ', '')
        # stock_code = stock['f12']
        stock_increase = float(stock['f3'])
        result.append([name, precent, pe_rate, stock_increase])

    show(fund_name, fund_code, result, today_increase)


print('[*] searching')

fund_codes = ['161725', '003095', '008750', '320007', '001156']  # 基金代码
for code in fund_codes:
    get_fund_info(code)

print('\n[*] done')
