from aurora_echo import echo_clone, echo_new, echo_modify, echo_promote, echo_retire  # noqa: F401
from aurora_echo.entry import root


# Entry for setuptools
def main():
    """
    Bringing you yesterday's database today!
    """
    root()


if __name__ == '__main__':
    main()
