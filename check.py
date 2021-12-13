import getopt
import sys
from parsers.LinkParser import LinkParser

if __name__ == '__main__':
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, 'l:', ['foperand', 'soperand'])
        if len(opts) != 1:
            raise getopt.GetoptError()
        else:
            link_parser = LinkParser(opts[0][1])
            channel = link_parser.parse()
            print(channel.serialize())
    except getopt.GetoptError:
        print ('Expected -l argument')
        sys.exit(2)
