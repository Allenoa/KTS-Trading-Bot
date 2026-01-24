from sheet_logger import log_to_sheet
from kis_api import KISApi

def test_sheet_logger():
    report_type = "중간점검"
    start_money = 1000000
    current_money = 990000
    profit = -100000

    log_to_sheet(report_type, start_money, current_money, profit)

def test_stock_name():
    api = KISApi()
    print(api.get_stock_name("034020"))

# if __name__ == "__main__":
#     test_sheet_logger()

if __name__ == "__main__":
    test_stock_name()