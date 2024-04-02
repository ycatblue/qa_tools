# -*- coding: utf-8 -*-
import argparse
import csv
import logging

from edp_eod.common.utils import download_eod, get_date, validate_date_format
import yaml
from model.logger import setup_logger


class Validator:
    def __init__(self, env, filename, logger):
        self.env = env
        self.filename = filename
        self.logger = logger
        self.data_list = []
        self.current_field = []
        # 定义常量
        self.EDP_HRT_ORDER = "EDP_HRT_Order"
        self.RSEC_MARKET_DATA = "EDP_RSec_MarketData"
        self.RSEC_ORDER = "EDP_RSec_Order"
        self.VALID_SIDES = ["1", "2"]
        self.VALID_MARKET = "EDP"
        self.VALID_QUOTE_VENUE = "XTKS"
        self.VALID_TIME_IN_FORCE = "0"
        self.VALID_TIME = ["ToSTNeTTransactionTime", "TradeTime", "QuoteTime", "TransactionTime"]
        self.VALID_BBO = ["PrimaryLastPx", "PrimaryBidPx", "PrimaryAskPx"]

    def data_generation(self):
        # 下载报告文件
        download_eod(self.env, self.filename)

        open_file = "{}_{}.csv".format(self.filename, get_date())
        self.logger.info(open_file)
        with open('temp_file/' + open_file, 'r') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader) # 获取表头
            self.current_field = header
            # 循环读取数据存入列表
            for row in csv_reader:
                data_dict = dict(zip(header, row))
                self.data_list.append(data_dict)

    # 判断字段是否存在并且顺序正常
    def validate_eod_field(self):
        with open('cfg/edp_filed.yaml', 'r') as file:
            yaml_data = file.read()
            data = yaml.safe_load(yaml_data)
            accept_field = data[self.filename]

            for current, accept in zip(self.current_field, accept_field):
                if current != accept:
                    self.logger.error(f"Field not inconsistency: current:{current}，accept:{accept}")
            self.logger.info(f"字段验证完成")

    # 判断数据是否正常
    def validate_eod_data(self):
        self.data_generation()
        self.validate_eod_field()
        errors = []

        with open('cfg/edp_field.yaml', 'r') as file:
            yaml_data = file.read()
            data = yaml.safe_load(yaml_data)
            fields = data[self.filename]

        # 打印数据列表
        self.logger.info("数据格式验证种")
        for data_dict in self.data_list:
            for recv_val in data_dict:
                for field in fields:
                    if recv_val == field:
                        # 判空
                        if not data_dict[field]:
                            self.logger.info(f'{field} not inconsistency,OrderID:{data_dict["OrderID"]}')

                        # 判值及类型
                        if recv_val in self.VALID_TIME:
                            if not validate_date_format(data_dict[field]):
                                self.logger.info(f'{field} not inconsistency,OrderID:{data_dict["OrderID"]}')

                        if recv_val in self.VALID_BBO and data_dict[
                            field] == "0.0000" and self.filename != self.RSEC_ORDER:
                            # 判断BBO是否为0.0000
                            self.logger.info(f'{field} not inconsistency,OrderID:{data_dict["OrderID"]}')
                            # 判断Account是否为当前环境的Account
                            if recv_val == 'Account' and f'R{self.env}_EDP_ACCOUNT_' not in data_dict[
                                "Account"] and self.filename != 'EDP_HRT_Trade':
                                self.logger.info(f'Account not inconsistency,OrderID:{data_dict["OrderID"]}')

                            # 判断Symbol格式是否正确
                            if recv_val == 'Symbol' and (
                                    self.filename != self.EDP_HRT_ORDER and ".EDP" in data_dict["Symbol"]) or (
                                    self.filename == self.EDP_HRT_ORDER and ".EDP" not in data_dict["Symbol"]):
                                self.logger.info(f'{field} not inconsistency,OrderID:{data_dict["OrderID"]}')

                            for accepted_field, accepted_value in fields.items():
                                if field == accepted_field:
                                    if accepted_value:
                                        if data_dict[field] not in accepted_value:
                                            if field not in ["TradePrice", "TradeQty"]:
                                                self.logger.info(
                                                    f'{field} not inconsistency,OrderID:{data_dict["OrderID"]}')
        self.logger.info('数据验证完成')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', default='UAT', help='1、SIT 2、UAT')
    parser.add_argument('-f', default='EDP_RSec_Order',
                        help='1、EDP_RSec_Trade 2、EDP_HRT_Trade 3、EDP_HRT_Order 4、EDP_RSec_MarketData 5、EDP_RSec_Order')
    args = parser.parse_args()

    # report
    setup_logger('self.logger', '{}_report.log'.format(args.f))
    logfix = logging.getLogger('self.logger')
    validator = Validator(args.e, args.f, logfix)
    validator.validate_eod_data()


if __name__ == '__main__':
    main()