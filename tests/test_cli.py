import pytest

import core.cli
from core.cli import main


def test_check_command(capsys):
    assert main(["check"]) == 0

    output = capsys.readouterr().out
    assert "Python:" in output
    assert "Platform:" in output
    assert "Core: OK" in output


def test_version_argument(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])

    assert exc.value.code == 0
    assert core.cli.__version__ in capsys.readouterr().out


def test_no_arguments_prints_help(capsys):
    assert main([]) == 0

    output = capsys.readouterr().out
    assert "usage:" in output
    assert "check" in output
    assert "plugins" in output


def test_plugins_reports_no_plugins(tmp_path, capsys):
    assert main(["plugins", "--directory", str(tmp_path)]) == 0

    output = capsys.readouterr().out
    assert "No plugins found." in output
    assert "WARNING:" in output


def test_plugins_are_sorted_and_missing_version_uses_unknown(
    tmp_path, monkeypatch, capsys
):
    class FakeLoader:
        def __init__(self, directory):
            self.directory = directory
            self.metadata = {
                "zeta": {"version": "2.0.0"},
                "alpha": {},
            }

        def load_all(self):
            return {
                "zeta": object(),
                "alpha": object(),
            }

    monkeypatch.setattr(core.cli, "PluginLoader", FakeLoader)

    assert main(["plugins", "--directory", str(tmp_path)]) == 0

    output = capsys.readouterr().out
    alpha_position = output.index("alpha unknown")
    zeta_position = output.index("zeta 2.0.0")

    assert alpha_position < zeta_position


@pytest.mark.parametrize(
    "error_type",
    [OSError, ValueError, ImportError, TypeError],
)
def test_plugins_loading_errors_are_handled(
    tmp_path, monkeypatch, capsys, error_type
):
    class FailingLoader:
        def __init__(self, directory):
            pass

        def load_all(self):
            raise error_type("test failure")

    monkeypatch.setattr(core.cli, "PluginLoader", FailingLoader)

    assert main(["plugins", "--directory", str(tmp_path)]) == 1

    output = capsys.readouterr().out
    assert "Plugin loading failed: test failure" in output
