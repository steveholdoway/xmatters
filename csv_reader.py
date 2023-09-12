import csv

def grab ( CSVFile ):
    datadict = []

    with open(CSVFile, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            # Skip blank rows, and comments and build a key/value pair with the first col as key, rest as value list. All trimmed ready
            if len(row) > 0 and len(row[0].strip()) > 0 and row[0].strip()[0] != '#':
                datadict.append({'key' : row[0].strip(), 'value': [i.strip() if type(i) == str else i for i in row[1:]]})

    return datadict

