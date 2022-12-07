import openpyxl

excel_file = openpyxl.load_workbook('urls_base.xlsx')

# sheet names
print(excel_file.sheetnames)
