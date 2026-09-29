#!/usr/bin/env python3
"""Build inside-bubble-bobble.md, the whole article as one file, from chapters/."""
import glob
import os

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    chapters = sorted(glob.glob(os.path.join(ROOT, 'chapters', '*.md')))
    text = ''.join(open(f).read() + '\n' for f in chapters).replace('../img/', 'img/')
    with open(os.path.join(ROOT, 'inside-bubble-bobble.md'), 'w') as f:
        f.write(text[:-1])


if __name__ == '__main__':
    main()
