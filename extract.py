import os
import re
import shutil
import sqlite3
import sys


def select_deck(c, msg):
    decks = []
    for row in c.execute('SELECT id, name FROM decks'):
        d_id = row[0]
        d_name = row[1]
        decks.append((d_id, d_name))

    print('{} (enter the number)'.format(msg))

    for i in range(len(decks)):
        print(' [{}] {}'.format(i, decks[i][1]))
    inp = int(input(''))
    return decks[inp][0]


def get_note_ids(c, deck_id):
    note_ids = []
    for row in c.execute(
        (
            'SELECT id FROM notes WHERE id IN '
            '(SELECT nid FROM cards WHERE did = ?) '
            'ORDER BY id'
        ),
        (deck_id,)
    ):
        nid = row[0]
        note_ids.append(nid)
    return note_ids


def select_note_fields(c, note_id):
    example_row = c.execute(
        'SELECT flds FROM notes WHERE id = ?', (note_id,)
        ).fetchone()
    example_flds = example_row[0].split('\x1f')
    for i in range(len(example_flds)):
        if len(example_flds[i]) > 0:
            print(' [{}] {}'.format(i, example_flds[i][:20]))
    print('Select the expression field. (enter the number) ')
    expr_idx = int(input(''))
    print('Select the reading field. (enter the number) ')
    read_idx = int(input(''))
    print('Select the meaning field. (enter the number) ')
    mean_idx = int(input(''))
    return expr_idx, read_idx, mean_idx


def extract(anki_path):
    anki_db_fp = os.path.join(
        anki_path,
        'collection.anki2'
    )
    anki_media_path = os.path.join(
        anki_path,
        'collection.media'
    )

    # open Anki DB
    conn = sqlite3.connect(anki_db_fp)
    c = conn.cursor()

    # figure out collection structure
    deck_id = select_deck(
        c,
        'Which deck to extract from?'
    )
    note_ids = get_note_ids(c, deck_id)
    expr_idx, read_idx, mean_idx = select_note_fields(
        c,
        note_ids[0]
    )

    # find images
    img_patt = re.compile(r'<img src="([^"]+)">')
    img_cards = []
    for nid in note_ids:
        row = c.execute(
            'SELECT flds FROM notes WHERE id = ?',
            (nid,)
        ).fetchone()
        flds_str = row[0]
        if img_patt.search(flds_str) is not None:
            shown_with = {
                'expr': False,
                'read': False,
                'mean': False,
            }
            fields = flds_str.split('\x1f')
            expr_field = fields[expr_idx].strip()
            read_field = fields[read_idx].strip()
            mean_field = fields[mean_idx].strip()
            if img_patt.search(expr_field):
                shown_with['expr'] = True
            elif img_patt.search(read_field):
                shown_with['read'] = True
            elif img_patt.search(mean_field):
                shown_with['mean'] = True
            img_card = {
                    'expr': expr_field,
                    'img_fns': [],
                    'shown_with': shown_with.copy()
                }
            for m in img_patt.findall(flds_str):
                img_card['img_fns'].append(m)
            img_cards.append(img_card)

    # prepare output
    out_path = f'imgs_{deck_id}'
    os.mkdir(out_path)
    os.mkdir(os.path.join(out_path, 'img'))
    tbl_lines = []

    for img_card in img_cards:
        web_img_paths = []
        for img_fn in img_card['img_fns']:
            # copy all over
            org_img_path = os.path.join(anki_media_path, img_fn)
            new_img_path = os.path.join(
                os.getcwd(), out_path, 'img', img_fn
            )
            web_img_paths.append(os.path.join('img', img_fn))
            shutil.copy(
                org_img_path,
                new_img_path
            )
        tbl_line_imgs = '<br>'.join(
            [
                f'<img src="{img_path}">'
                for img_path in web_img_paths
            ]
        )
        tbl_lines.append(
            '<tr><td>{}</td><td>{}</td></tr>'.format(
                img_card['expr'],
                tbl_line_imgs
            )
        )

    with open(os.path.join(out_path, 'index.html'), 'w') as f:
        f.write('<html><head><style>\n')
        f.write('table { border-collapse: collapse; }\n')
        f.write('td { border: solid 1px #000; }\n')
        f.write('img { margin: 3px; }\n')
        f.write('</head></style>\n')
        f.write('<body><table>\n')
        for line in tbl_lines:
            f.write(f'{line}\n')
        f.write('</table></body></html>')


if __name__ == '__main__':
    anki_path = sys.argv[1]
    extract(anki_path)
