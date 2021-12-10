import xlsxwriter


class XLSXFileProcessor:
    def __init__(self, fields_config, xlsx_filename):
        self.fields_config = fields_config
        self.filename = xlsx_filename

    def format_item(self, item):
        result = {}
        for field in self.fields_config.keys():
            keys = field.split('.')
            keys_count = len(keys)
            value = None
            depth_object = item
            for i in range(keys_count):
                if i == keys_count - 1 and keys[i] in depth_object:
                    value = depth_object[keys[i]]
                else:
                    if keys[i] in depth_object:
                        depth_object = depth_object[keys[i]]
                    else:
                        break
            if value:
                result[self.fields_config[field]] = value
        return result

    def convert(self, input_items_list):
        print(input_items_list)
        workbook = xlsxwriter.Workbook(self.filename, {'strings_to_urls': False})
        worksheet = workbook.add_worksheet()
        headers = list(self.fields_config.values())
        for i in range(len(headers)):
            worksheet.write(0, i, headers[i])
        items = map(self.format_item, input_items_list)

        for index, item in enumerate(items):
            for i, header in enumerate(headers):
                if header in item:
                    worksheet.write(index + 1, i, item[header])
        workbook.close()
