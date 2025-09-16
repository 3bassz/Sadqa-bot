# imghdr.py - بديل بسيط لموديول imghdr المحذوف
import mimetypes
import os

def what(file, h=None):
    # تحديد نوع الصورة باستخدام الامتداد فقط
    if isinstance(file, (str, bytes, os.PathLike)):
        mime, _ = mimetypes.guess_type(file)
        if mime and mime.startswith("image/"):
            return mime.split("/")[-1]
    return None
