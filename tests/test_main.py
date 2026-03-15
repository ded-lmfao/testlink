import sys
from unittest.mock import MagicMock, patch


def test_main_version_flag():
    # Mocking sys.argv to include --version
    # Mocking subprocess.check_output to avoid actual java call
    # Mocking print to capture output

    # We use a patch on sys.modules to avoid side effects of importing the module multiple times
    # or failing due to missing java.

    mock_subprocess = MagicMock()
    mock_subprocess.check_output.return_value = b'openjdk version "17.0.1" 2021-10-19'

    with patch("sys.argv", ["revvlink", "--version"]):
        with patch("subprocess.check_output", mock_subprocess.check_output):
            with patch("platform.platform", return_value="macOS-test"):
                with patch("builtins.print") as mock_print:
                    # Import the module to trigger its execution
                    sys.modules.pop("revvlink.__main__", None)
                    import revvlink.__main__  # noqa: F401

                    mock_print.assert_called()
                    args_list = mock_print.call_args[0][0]
                    assert "revvlink:" in args_list
                    assert "Python:" in args_list
                    assert "macOS-test" in args_list


def test_main_no_flag():
    with patch("sys.argv", ["revvlink"]):
        with patch("builtins.print") as mock_print:
            if "revvlink.__main__" in sys.modules:
                del sys.modules["revvlink.__main__"]
            import revvlink.__main__  # noqa: F401

            mock_print.assert_not_called()
