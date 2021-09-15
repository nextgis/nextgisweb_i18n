from pathlib import Path

from ngwdocker import PackageBase
from ngwdocker.base import AppImage
from ngwdocker.util import copyfiles, git_ls_files


class Package(PackageBase):
    target_ngw = False


PTH = '${NGWROOT}/package/nextgisweb_i18n'
ENV = 'NEXTGISWEB__CORE__LOCALE__EXTERNAL_PATH'


@AppImage.on_virtualenv.handler
def on_virtualenv(event):
    if event.image.context.is_production():
        src = Path(__file__).parent
        copyfiles(git_ls_files(src), event.source / 'nextgisweb_i18n', src)
        event.commands_after_install.insert(0, "export {}={}".format(ENV, PTH))


@AppImage.on_config.handler
def on_config(event):
    event.image.config_set('core', 'locale.external_path', PTH)
    event.image.config_set('core', 'locale.poeditor.project_id', '435991')