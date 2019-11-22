import dropbox


class Dropbox_api(object):
    def __init__(self, access_token):
        self.dbx = dropbox.Dropbox(access_token)

    def upload(self, data, path, overwrite=False):
        mode = (dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add)
        try:
            res = self.dbx.files_upload(
                data, path, mode, mute=True)
        except dropbox.exceptions.ApiError as err:
            print('*** API error', err)
            return None
        return res
