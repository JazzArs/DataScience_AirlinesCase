import csv
import os
import sys

translit_map = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
    'Е': 'E', 'Ё': 'E', 'Ж': 'ZH', 'З': 'Z', 'И': 'I',
    'Й': 'I', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
    'У': 'U', 'Ф': 'F', 'Х': 'KH', 'Ц': 'TS', 'Ч': 'CH',
    'Ш': 'SH', 'Щ': 'SHCH', 'Ы': 'Y', 'Ь': 'IE', 'Э': 'E',
    'Ю': 'IU', 'Я': 'IA',
}

for k, v in list(translit_map.items()):
    translit_map[k.lower()] = v.capitalize()


def transliterate(text: str) -> str:
    return ''.join(translit_map.get(ch, ch) for ch in text)


def detect_delimiter(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        line = f.readline()
        if line.count(';') > line.count(','):
            return ';'
        return ','


def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.isfile(input_file):
        sys.exit(1)

    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_translit{ext}"

    delimiter = detect_delimiter(input_file)

    with open(input_file, 'r', encoding='utf-8-sig', newline='') as infile, \
            open(output_file, 'w', encoding='utf-8', newline='') as outfile:

        reader = csv.DictReader(infile, delimiter=delimiter)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames, delimiter=delimiter)
        writer.writeheader()

        for row in reader:
            cleaned_row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}

            if 'real_first_name' in cleaned_row:
                cleaned_row['real_first_name'] = transliterate(cleaned_row['real_first_name'])
            if 'real_last_name' in cleaned_row:
                cleaned_row['real_last_name'] = transliterate(cleaned_row['real_last_name'])

            writer.writerow(cleaned_row)


if __name__ == "__main__":
    main()
