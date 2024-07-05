const MyLang = {
  msgData: {
    "TXT_EXTENSION_NAME": chrome.i18n.getMessage('extension_name'),
    "TXT_EXTENSION_DESCRIPTION": chrome.i18n.getMessage('extension_description'),
  },

  /**
   * getMsg
   *
   * メッセージ取得
   *
   * @param {String} aMsgCd メッセージコード
   * @return {String} 国際化メッセージ
   */
  getMsg: function (aMsgCd) {
    let text = MyLang.msgData[aMsgCd];

    if (typeof (text) == 'undefined') {
      text = aMsgCd;
    }

    return text
  },
}