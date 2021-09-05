class TazDownloadFormatException(Exception):

    def __inti__(self, format: str):
        self.format = format

    def __str__(self):
        return f"\"{self.format}\" is not a valid download format." \
               f"\nValid formats are: pdf, epub, epubt, html, ascii, mobi, mobit"


class TazDownloadError(Exception):

    def __inti__(self, format: str):
        self.format = format


class TazConfigurationError(Exception):

    def __inti__(self, misconfiguration: str):
        self.misconfiguration = misconfiguration

    def __str__(self):
        return f"\"{self.misconfiguration}\" must be defined either in the config.yaml or by passing it as an argument."
