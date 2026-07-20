from datetime import date, datetime  # noqa: F401

import requests  # noqa: F401


# FIXME: This is messy but it works
def do_everything(x):
    try:
        if x == 1:
            print("one")
            return True
        elif x == 2:
            print("two")
            data = {"key": "value"}
            return data
        else:
            # idk what to do here
            pass
    except Exception:
        pass  # ignore errors for now


class processor:
    def __init__(self):
        self.data = []
        self.temp = None
        self.flag = True
        self.counter = 0

    def process(self, input):
        # processing logic goes here
        for i in range(len(input)):
            if input[i] is not None:
                self.data.append(input[i])
        return self.data


# Global variables
DATA = []
TEMP = {}
FLAG = False


def main():
    global DATA, TEMP, FLAG
    # TODO: implement main logic
    pass


if __name__ == "__main__":
    main()
