/** start - VALUE CONSTANT AND GLOBAL */
const DEBUG_MODE = true;

const SERVER_URL = 'https://sateraito-gpt-api.appspot.com';
const PREFIX_KEY = 'Sateraito-WzNyEGIZoaF7Z1R8';
/** end - VALUE CONSTANT AND GLOBAL */


/** start - DATA DEFAULT */

/** end - DATA DEFAULT */


/**
 * My Utils
 * 
 */
const MyUtils = {
  flagHasSetCloseSidePanel: false,
  flagHasSetClearSidePanel: false,

  /**
   * Debug log
   * @param {string} strMsg
   */
  debugLog: (strMsg) => {
    if (DEBUG_MODE === true) {
      console.log(chrome.i18n.getMessage('@@extension_id') + ' ' + (new Date()).toLocaleString() + ':', strMsg);
    }
  },

  /**
   * encodeBase64
   * 
   * @param {string} value 
   * @returns {string}
   */
  encodeBase64: (value) => {
    const encodedWord = CryptoJS.enc.Utf8.parse(value);
    const encoded = CryptoJS.enc.Base64.stringify(encodedWord);
    return encoded;
  },

  /**
   * decodeBase64
   * 
   * @param {string} value 
   * @returns {string}
   */
  decodeBase64: (value) => {
    // PROCESS
    const encodedWord = CryptoJS.enc.Base64.parse(value);
    const decoded = CryptoJS.enc.Utf8.stringify(encodedWord);
    return decoded;
  },

  toUpperCaseFirst: (text) => {
    return text.charAt(0).toUpperCase() + text.slice(1);
  },

  /**
   * generateToken
   * 
   * @returns {string}
   */
  generateToken: () => {
    let date_str = MyUtils.getDateUTCString();
    return CryptoJS.MD5(PREFIX_KEY + date_str);
  },

  /**
   * generateTokenByTenant
   * 
   * @param {string} tenant 
   * @returns {string}
   */
  generateTokenByTenant: (tenant) => {
    let date_str = MyUtils.getDateUTCString();
    return CryptoJS.MD5(tenant + date_str);
  },

  /**
   * getDateUTCString
   * 
   * @returns {string}
   */
  getDateUTCString: () => {
    let curr_date = new Date();
    let dt_str = curr_date.getUTCFullYear() +
      ('00' + (curr_date.getUTCMonth() + 1)).slice(-2) +
      ('00' + curr_date.getUTCDate()).slice(-2) +
      ('00' + curr_date.getUTCHours()).slice(-2) +
      ('00' + curr_date.getUTCMinutes()).slice(-2);
    return dt_str;
  },

  /**
   * Render text to element style chat GPT
   * 
   * @param {element} elToRender 
   * @param {string} stringRender 
   * @param {Function} callback 
   */
  renderTextStyleChatGPT: (elToRender, stringRender, callback) => {
    let indexText = 0;
    let timeT = setInterval(() => {
      elToRender.innerHTML += stringRender[indexText];
      indexText++;
      if (indexText >= stringRender.length) {
        clearInterval(timeT);

        if (callback) {
          callback(elToRender);
        }
      }
    }, 5);
  },

  /**
   * Get radom string
   * 
   * @returns {string}
   */
  randomId: () => {
    return Math.random().toString(36).slice(-8);
  },

  /**
   * Get new id
   * 
   * @returns {string}
   */
  getNewId: () => {
    const self = MyUtils;

    let idNew = self.randomId();

    if ($(`#${idNew}`).length == 0) {
      return idNew;
    }

    return self.getNewId();
  },

  /**
   * setOpenSidePanel
   * 
   */
  setOpenSidePanel: () => {
    const self = MyUtils;

    // open side panel when action for compose
    chrome.runtime.sendMessage({
      method: 'open_side_panel',
    })
  },
};

/**
 * _Storage Manager
 * 
 */
const _StorageManager = {
  // For Auth
  setAccessTokenCache: (access_token, expiryInMinutes = 5, callback) => {
    const now = new Date();
    const expiryTime = new Date(now.getTime() + expiryInMinutes * 60000);

    const tokenData = {
      value: access_token,
      expiry: expiryTime.toISOString()
    };

    chrome.storage.local.set({ user_access_token: tokenData }, () => {
      if (callback) {
        callback();
      }
    });
  },
  getAccessTokenCache: (callback) => {
    chrome.storage.local.get('user_access_token', payload => {
      callback(payload.user_access_token)
    });
  },
  removeAccessTokenCache: () => {
    chrome.storage.local.remove('user_access_token');
  },

  setUserInfoCache: (userInfo, callback) => {
    chrome.storage.local.set({ user_info: userInfo }, () => {
      if (callback) {
        callback();
      }
    });
  },
  getUserInfoCache: (callback) => {
    chrome.storage.local.get('user_info', payload => {
      callback(payload.user_info)
    });
  },
  removeUserInfoCache: () => {
    chrome.storage.local.remove('user_info');
  },
  // 
};

/**
 * Sateraito Request
 * 
 */
const SateraitoRequest = {

};

const Authorization = {
  _getRequest: (url, callback) => {
    const self = Authorization;

    self.getAccessToken(accessToken => {
      // Action call request
      fetch(url,
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          },
        })

        // handler for response success
        .then(async dataRes => {
          let jsonData = await dataRes.json();
          callback(true, jsonData);
        })

        // handler for request or response is error
        .catch(error => {
          callback(false, undefined);
        })
    });

  },
  _postRequest: (url, data, callback) => {
    const self = Authorization;

    self.getAccessToken(accessToken => {
      // Action call request
      fetch(url,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${accessToken}`
          },
          body: JSON.stringify(data)
        })

        // handler for response success
        .then(async dataRes => {
          let jsonData = await dataRes.json();
          callback(true, jsonData);
        })

        // handler for request or response is error
        .catch(error => {
          callback(false, undefined);
        })
    });

  },

  /**
   * getAccessToken
   *  
   * @param {Function} callback 
   */
  getAccessToken: (callback) => {
    _StorageManager.getAccessTokenCache(tokenInfo => {
      if (!tokenInfo) {
        callback(false);
        return;
      }

      const now = new Date();

      if (now.toISOString() > tokenInfo.expiry) {
        MyUtils.debugLog('OVER TIME TOKEN - Try get new access token');

        chrome.identity.getAuthToken({ interactive: false }, token => {
          _StorageManager.setAccessTokenCache(token);
          callback(token);
        });

      } else {
        callback(tokenInfo.value);
      }
    })
  },

  /**
   * getUserInfo
   *  
   * @param {Function} callback 
   */
  getUserInfo: (callback) => {
    const self = Authorization;

    _StorageManager.getUserInfoCache(userInfoCache => {
      if (userInfoCache) {
        callback(userInfoCache);

      } else {
        self._getRequest(`https://www.googleapis.com/oauth2/v1/userinfo`, (success, userInfo) => {
          if (success) {
            _StorageManager.setUserInfoCache(userInfo);
            callback(userInfo);
          } else {
            callback(undefined);
          }
        })
      }
    });
  },

  /**
   * checkUserLogin
   *  
   * @param {Function} callback 
   */
  checkUserLogin: (callback) => {
    const self = Authorization;

    self.getAccessToken(accessToken => {
      callback(accessToken && typeof accessToken != 'undefined');
    });

  },

  /**
   * handlerLogin
   *  
   * @param {Function} callback 
   */
  handlerLogin: (callback) => {
    const self = Authorization;

    // chrome.identity.getAuthToken({ interactive: true }, token => {
    //   if (callback) {
    //     _StorageManager.setAccessTokenCache(token);
    //
    //     callback(token);
    //   }
    // });
    window.open(`${SERVER_URL}/a/login`)
  },

  /**
   * handlerLogout
   *  
   * @param {Function} callback 
   */
  handlerLogout: (callback) => {
    const self = Authorization;

    try {

      _StorageManager.removeUserInfoCache();
      _StorageManager.removeAccessTokenCache();

      return callback(true);

    } catch (error) {
      callback(false);
    }
  },
};