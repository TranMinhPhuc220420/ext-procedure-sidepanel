/** start - VALUE CONSTANT AND GLOBAL */
const DEBUG_MODE = true;

const SERVER_URL = 'https://ext2005-dot-vn-sateraito-apps-fileserver2.appspot.com';
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

    chrome.storage.local.set({user_access_token: tokenData}, () => {
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

  setUserLogin: (user, callback) => {
    chrome.storage.local.set({user_login: user}, () => {
      if (callback) {
        callback();
      }
    });
  },
  getUserLogin: (callback) => {
    chrome.storage.local.get('user_login', payload => {
      callback(payload.user_login)
    });
  },
  removeUserLogin: () => {
    chrome.storage.local.remove('user_login');
  },

  // 
};

/**
 * Sateraito Request
 *
 */
const SateraitoRequest = {
  _get: (url, callback) => {
    const self = Authorization;

    // Action call request
    fetch(url,
      {
        headers: {},
      })

      // handler for response success
      .then(async dataRes => {
        let jsonData = await dataRes.json();

        let isSuccess = true;
        if ('status' in jsonData) {
          if (jsonData['status'] != 'ok') {
            isSuccess = false;
          }
        }

        let data = jsonData;
        if ('data' in jsonData) {
          data = jsonData['data'];
        }

        callback(isSuccess, data);
      })

      // handler for request or response is error
      .catch(error => {
        callback(false, undefined);
      })
  },

  _post: (url, data, callback) => {
    const self = Authorization;

    // Action call request
    fetch(url,
      {
        method: 'POST',
        headers: {},
        body: JSON.stringify(data)
      })

      // handler for response success
      .then(async dataRes => {
        let jsonData = await dataRes.json();

        let isSuccess = true;
        if ('status' in jsonData) {
          if (jsonData['status'] != 'ok') {
            isSuccess = false;
          }
        }

        let data = jsonData;
        if ('data' in jsonData) {
          data = jsonData['data'];
        }

        callback(isSuccess, data);
      })

      // handler for request or response is error
      .catch(error => {
        callback(false, undefined);
      })
  },
};

/**
 * FirebaseManager
 *
 */
const FirebaseManager = {
  _config: null,
  _app: null,
  _database: null,

  _init: () => {
    const self = FirebaseManager;

    self.loadConfig(webappConfig => {
      if (typeof webappConfig == 'undefined') {
        console.warn('WEBAPP CONFIG FIREBASE IS ERROR')
        return;
      }

      self._config = webappConfig;

      // Initialize Firebase
      self._app = firebase.initializeApp(self._config);
      self._database = firebase.database();
    });
  },

  loadConfig: (callback) => {
    SateraitoRequest._post(`${SERVER_URL}/api/webapp/config`, {'config_get': 'firebase_config'}, (success, webappConfig) => {
      callback(success ? webappConfig : undefined);
    });
  },
};

/**
 * Authorization
 *
 */
const Authorization = {
  info: null,

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

        // TODO:: Send request get access token
        //  _StorageManager.setAccessTokenCache(token);
        //  callback(token);

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

    SateraitoRequest._get(`${SERVER_URL}/api/auth/get-info`, (success, userInfo) => {
      if (success) {

        _StorageManager.setUserLogin(userInfo);

        callback(userInfo);
      } else {
        callback();
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

    self.getUserInfo(userInfo => {
      callback(typeof userInfo != 'undefined');
    });
  },

  /**
   * handlerLogin
   *
   * @param {Function} callback
   */
  handlerLogin: (callback) => {
    const self = Authorization;

    const width = 500;
    const height = 600;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;
    const specs = `width=${width},height=${height},top=${top},left=${left},status=no,toolbar=no,menubar=no,location=no,resizable=yes,scrollbars=yes`;

    window.open(`${SERVER_URL}/a/login`, '_blank', specs);

    // Function to handle incoming messages from the login window
    function receiveMessage(event) {
      // Process the received message
      console.log('Received message from login window:', event.data);

      self.getUserInfo(userInfo => {
        callback(event.data == 'success', userInfo)
      });
    }

    // Add an event listener for messages
    window.addEventListener('message', receiveMessage, false);
  },

  /**
   * handlerLogout
   *
   * @param {Function} callback
   */
  handlerLogout: (callback) => {
    const self = Authorization;

    try {

      const width = 500;
      const height = 600;
      const left = (window.screen.width - width) / 2;
      const top = (window.screen.height - height) / 2;
      const specs = `width=${width},height=${height},top=${top},left=${left},status=no,toolbar=no,menubar=no,location=no,resizable=yes,scrollbars=yes`;

      const logoutWindow = window.open(`${SERVER_URL}/a/logout`, '_blank', specs);

      // Function to handle incoming messages from the login window
      function receiveMessage(event) {
        // Process the received message
        console.log('Received message from login window:', event.data);

        logoutWindow.close();

        _StorageManager.removeUserLogin();
        _StorageManager.removeAccessTokenCache();

        callback(true);
      }

      // Add an event listener for messages
      window.addEventListener('message', receiveMessage, false);

    } catch (error) {
      callback(false);
    }
  },
};