class TazDownloadFormatException(Exception):

    def __inti__(self, format: str):
        self.format = format

    def __str__(self):
        return f"\"{self.format}\" is not a valid download format." \
               f"\nValid formats are: pdf, epub, epubt, html, ascii, mobi, mobit"


class TazDownloadError(Exception):

    def __inti__(self, format: str):
        self.format = format
