#-*- coding: utf-8 -*-
#fstream https://github.com/Kodi-fstream/venom-xbmc-addons
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.parser import cParser
from resources.hosters.hoster import iHoster


class cHoster(iHoster):

    def __init__(self):
        iHoster.__init__(self, 'axavid', 'Axavid')

    def _getMediaLinkForGuest(self):
        oRequest = cRequestHandler(self._url)
        sHtmlContent = oRequest.request()

        sPattern = 'file: "([^"]+)"'

        oParser = cParser()
        sHtmlContent=sHtmlContent.replace('|','/')
        aResult = oParser.parse(sHtmlContent, sPattern)


        if aResult[0] is True:
            api_call = aResult[1][0]
            return True, api_call

        return False, False
