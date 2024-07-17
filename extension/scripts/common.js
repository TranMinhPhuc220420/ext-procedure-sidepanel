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

  /**
   * getDomainEmail
   *
   * @param {string} email
   * @returns {string}
   */
  getDomainEmail: (email) => {
    return email.split('@')[1];
  },

  /**
   * toPathDomain
   *
   * @param {string} domain
   * @returns {string}
   */
  toPathDomain: (domain) => {
    return domain.replaceAll('.', '__');
  }
};

/**
 * _Storage Manager
 *
 */
const _StorageManager = {};

/**
 * Sateraito Request
 *
 */
const SateraitoRequest = {
  /**
   * Request method GET
   *
   * @param {string} url
   * @param {Function} callback
   */
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

  /**
   * Request method POST
   *
   * @param {string} url
   * @param {Object} data
   * @param {Function} callback
   * @private
   */
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

const WorkflowDocManager = {
  // Request API function

  /**
   * getNewIDRequest
   *
   * @return {Promise<Object|string>}
   */
  getNewIDRequest: () => {
    return new Promise((resolve, reject) => {
      const url = `${SERVER_URL}/api/workflow-doc/get-new-id`;
      SateraitoRequest._get(url, (success, data) => {
        if (success) {
          resolve(data);
        } else {
          reject('ERROR:: Workflow doc get new id');
        }
      });
    });
  },

  /**
   * createRequestCheckContentEmail
   *
   * @return {Promise<Object|string>}
   */
  createRequestCheckContentEmail: (user_email, params) => {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        {
          method: 'api_workflow_doc_create_request_check_content_email',
          payload: params
        }, (result) => {
          const {success, msg, data} = result;
          if (success) {
            resolve(data);
          } else {
            reject(msg);
          }
        });
    });
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
  _messaging: null,

  /**
   * Initialize firebase app
   *
   */
  _init: async (triggerEventAllowMail = false) => {
    const self = FirebaseManager;

    const firebaseConfig = await self.loadConfig();
    if (!firebaseConfig) {
      console.warn('WEBAPP CONFIG FIREBASE IS ERROR')
      return;
    }

    self._config = firebaseConfig;

    // Initialize Firebase
    self._app = firebase.initializeApp(self._config);

    if (firebase.database) {
      self._database = firebase.database();

      if (triggerEventAllowMail) {
        self.setTriggerEventRequestAllowMail()
      }
    }

    if (firebase.messaging) {
      self._messaging = firebase.messaging();
    }
  },

  /**
   * initMessaging
   *
   * @param {string} userEmail
   * @return {Promise<Object>}
   */
  initMessaging: (userEmail) => {
    const self = FirebaseManager;

    return new Promise((resolve, reject) => {
      if (!self._messaging) {
        reject({success: false, msg: 'Firebase messaging not install'});
        return;
      }

      self._messaging.onMessage(e => console.log('self._messaging.onMessage', e))
      self._messaging.getToken({vapidKey: self._config['vapidKey']}).then((currentToken) => {
        if (currentToken) {
          let values = {
            method: 'api_domain_set_token_notification',
            payload: {
              current_token: currentToken,
              user_email: userEmail,
              domain_email: MyUtils.getDomainEmail(userEmail)
            }
          }
          chrome.runtime.sendMessage(values, (result) => {
            resolve({success: true, msg: '', current_token: currentToken});
          });
        } else {
          reject({success: false, msg: 'No registration token available. Request permission to generate one.'});
        }
      }).catch((err) => {
        reject({success: false, msg: 'An error occurred while retrieving token. ' + err});
      });
    });
  },

  /**
   * Call request get config from server
   *
   * @return {Promise<Object>}
   */
  loadConfig: () => {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({method: 'api_firebase_load_config'}, (config) => {
        if (config) {
          resolve(config);
        } else {
          reject(config)
        }
      });
    })
  },

  // Functions for mail

  /**
   * addRequestCheckMailToAdmin
   *
   * @param {string} userEmail
   * @param {string} emailId
   */
  addRequestCheckMailToAdmin: (userEmail, emailId) => {
    const self = FirebaseManager;

    let email_domain = MyUtils.getDomainEmail(userEmail);
    let domain_path = MyUtils.toPathDomain(email_domain);

    let reference = self._database.ref(`${domain_path}/email_request_check_content`);

    let newRow = {};
    newRow[emailId] = false;

    let newChildRef = reference.push();
    newChildRef.set(newRow);
  },

  /**
   * setTriggerEventRequestAllowMail
   *
   */
  setTriggerEventRequestAllowMail: () => {
    const self = FirebaseManager;
    const domain_path = MyUtils.toPathDomain(MyUtils.getDomainEmail(Authorization.info.user_email));

    let reference = self._database.ref(`${domain_path}`);
    reference.on('value', (snapshot) => {
      const data = snapshot.val();
      console.log(data);
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
   * getUserInfo
   *
   * @param {Function} callback
   */
  getUserInfo: (callback) => {
    const self = Authorization;

    chrome.runtime.sendMessage({method: 'api_get_user_info'}, res => {
      self.info = res;
      callback(res);
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
      let isLogged = false;
      if (userInfo) {
        isLogged = true;
      }

      callback(isLogged);
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

        let isSuccess = false;
        if (userInfo) {
          isSuccess = true;
        }

        callback((event.data == 'success') && isSuccess, userInfo)
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

        callback(true);
      }

      // Add an event listener for messages
      window.addEventListener('message', receiveMessage, false);

    } catch (error) {
      callback(false);
    }
  },
};