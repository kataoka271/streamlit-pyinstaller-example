# Streamlit + Pyinstallerの構築パターン

## フォルダ構成

* streamlit-example/  プロジェクトルート
    * streamlit_app/
        * main.py  メインスクリプト
        * pages/
            * page1.py  ページ1
            * page2.py  ページ2
    * streamlit_pyinstaller/
        * hooks/
            * hook-streamlit.py  Streamlitのリソースデータ収集を行うフックファイル
            * hook-streamlit_folium.py  streamlit-foliumを使う場合、リソースファイルをコピーする必要があるため
        * run_main.py  PyinstallerのExeファイルのエントリポイント

## Streamlitアプリをパッケージとしてインストール

venvなどの仮想環境を使用している前提で、Streamlitアプリを.venvに編集可能パッケージとしてstreamlit_appを登録しておく。

```
pip install -e .
```
や
```
poetry install
```

```
streamlit run streamlit_app/main.py
```
で動作することを確認しておく。

## Pyinstallerエントリポイントの作成

streamlit_pyinstaller/run_main.py
```py
import os
import sys
from pathlib import Path

import streamlit.web.cli as stcli


def resolve_path(path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.getcwd())
    return str(Path(base_path) / path)


if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("main.py"),
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
```

streamlit_pyinstaller/hooks/hook-streamlit.py
```py
import site

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

site_packages_dir = site.getsitepackages()[0]
datas = [(f"{site_packages_dir}/streamlit/runtime", "./streamlit/runtime")]
datas = copy_metadata("streamlit")
datas += collect_data_files("streamlit")
hiddenimports = collect_submodules("streamlit")
```

run_main.pyはPyinstallerでEXE化したときのエントリポイントになる。Streamlitをサブプロセスで起動する。
sys._MEIPASSにPyinstallerのデータディレクトリ (_internal/ やTempディレクトリ) が入っているので、
これを参照してStreamlitアプリを起動する。

hook-streamlit.pyはStreamlitが使用するリソースファイルなどをコピーする。
これがないと、リソースが見つからないことによってStreamlit起動時にエラーが出る。

## Specファイルの作成

```
pyinstaller --additional-hooks-dir=./streamlit_pyinstaller/hooks --clean ./streamlit-pyinstaller/run_main.py
```
でspecファイルを作る。EXEも生成できるが、まだ、実行してもModule Not FoundでStreamlitが立ち上がらないはずである。

specファイルの以下2行を編集する。

run_main.spec
```py
a = Analysis(
    ...
    datas=[("streamlit_app/main.py", ".")],
    hiddenimports=["streamlit_app"],
    ...
```

datasで、Streamlitアプリmain.pyをPyinstallerの_internalルートにコピーする。
上述のように、Streamlitをサブプロセスとして起動し引数に実行スクリプトを要求するため、スクリプトをデータとして渡してあげる必要がある。

hiddenimportsには、Streamlitのメインスクリプト、ページを含むパッケージを指定する。
streamlit_app/__init__.pyにmainやpagesをモジュールとしてインポートしておけば、Pyinstallerが自動的に依存モジュールとして収集してくれる。


## EXEファイルの作成

2回目はspecファイルを指定してPyinstallerを実行する。

```
pyinstaller run_main.spec
```

出来上がったEXEはdistディレクトリ以下にある。実行するとStreamlitアプリが立ち上がるはずである。
