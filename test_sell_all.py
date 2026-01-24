from kis_api import KISApi

def sell_all():
    api = KISApi()
    api.sell_all_holdings()

if __name__ == "__main__":
    sell_all()