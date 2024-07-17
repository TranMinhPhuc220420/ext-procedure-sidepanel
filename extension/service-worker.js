(() => {
  /** start - VALUE CONSTANT AND GLOBAL */
  const MANIFEST = chrome.runtime.getManifest();
  const DEBUG_MODE = true;

  const SERVER_URL = 'https://ext2005-dot-vn-sateraito-apps-fileserver2.appspot.com';
  const PREFIX_KEY = 'Sateraito-WzNyEGIZoaF7Z1R8';
  /** end - VALUE CONSTANT AND GLOBAL */

  let USER_ADDON_LOGIN, EMAIL_USER_ADDON, DOMAIN_USER_ADDON = undefined;

  if (MANIFEST.manifest_version >= 3) {
    try {
      // only avable in manifest v3
      importScripts(
        "/third-party/firebase-10.12.3/firebase-app-compat.js",
        "/third-party/firebase-10.12.3/firebase-database-compat.js",
      );
    } catch (err) {
      console.error(err);
    }
  }

  const _getRequest = (url, callback) => {
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
  };
  const _postRequest = (url, data, callback) => {
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
  };

  const toPathDomain = (domain) => {
    return domain.replaceAll('.', '__');
  };

  const _Firebase_SW = {
    _config: null,
    _app: null,
    _database: null,
    _messaging: null,

    /**
     * Initialize firebase app of service worker
     *
     */
    _init: () => {
      const self = _Firebase_SW;

      self.loadConfig(firebaseConfig => {
        if (!firebaseConfig) {
          console.warn('WEBAPP CONFIG FIREBASE IS ERROR')
          return;
        }

        self._config = firebaseConfig;

        // Initialize Firebase
        self._app = firebase.initializeApp(self._config);

        if (firebase.database) {
          self._database = firebase.database();

          if (USER_ADDON_LOGIN['is_admin']) {
            self.setTriggerEventRequestAllowMail()
          }
        }
      });
    },

    loadConfig: (callback) => {
      if (self._config) {
        callback(true, self._config)
        return;
      }

      _postRequest(`${SERVER_URL}/api/webapp/config`, {'config_get': 'firebase_config'}, (success, webappConfig) => {
        callback(success ? webappConfig : undefined);
      });
    },

    setTriggerEventRequestAllowMail: () => {
      const self = _Firebase_SW;

      const domain_path = toPathDomain(DOMAIN_USER_ADDON);
      let reference = self._database.ref(`${domain_path}/email_request_check_content`);

      reference.on('value', (snapshot) => {
        const data = snapshot.val();
        console.log('Service worker: ', data);

        let totalNotSeen = 0;
        for (const key in data) {
          for (const key_2 in data[key]) {
            if (data[key][key_2] == false) {
              totalNotSeen++;
            }
          }
        }

        if (totalNotSeen > 0) {
          chrome.action.setBadgeText({text: totalNotSeen.toString()});
          chrome.action.setBadgeBackgroundColor({color: '#50d06a'});
        } else {
          chrome.action.setBadgeText({text: ''});
        }
      });
    },
  };

  const _Authorization_SW = {
    info: null,

    /**
     * getUserInfo
     *
     * @param {Function} callback
     */
    getUserInfo: (callback) => {
      const self = _Authorization_SW;

      if (self.info) {
        callback(self.info);
        return;
      }

      _getRequest(`${SERVER_URL}/api/auth/get-info`, (success, userInfo) => {

        self.info = userInfo;

        if (success) {
          callback(userInfo);
        } else {
          callback();
        }
      });
    },

    /**
     * setTokenNotification
     *
     * @param {Object} params
     * @param {Function} callback
     */
    setTokenNotification: (params, callback) => {
      const {domain_email, user_email, current_token} = params;

      const apiUrl = `${SERVER_URL}/${domain_email}/api/auth/set-token-notification`;
      const formValue = {
        'token_notification': current_token,
        'user_email': user_email
      };

      _postRequest(apiUrl, formValue, (success, result) => {
        callback(success ? result : undefined);
      });
    }
  };

  const _WorkflowDoc_SW = {
    // Request API function

    /**
     * getNewIDRequest
     *
     */
    getNewIDRequest: (callback) => {
      const url = `${SERVER_URL}/api/workflow-doc/get-new-id`;
      _getRequest(url, (success, data) => {
        if (success) {
          callback(data);
        } else {
          callback();
        }
      });
    },

    /**
     * createRequestCheckContentEmail
     *
     */
    createRequestCheckContentEmail: (params, callback) => {
      const {domain_email} = params;

      const url = `${SERVER_URL}/${domain_email}/api/workflow-doc/create-new-doc`;
      _postRequest(url, params, (success, data) => {
        if (success) {
          callback({success: true, msg: '', data: data});
        } else {
          callback({success: true, msg: 'create new doc error', data: data});
        }
      });
    },
  };

  const _Storage_SW = {
    onChanged: (payload, type) => {
      // if ('key' in payload) {
      //
      // }
    }
  };

  const onMessageSW = (request, sender, sendResponse) => {
    const {method, payload} = request;

    switch (method) {
      case 'open_side_panel':
        chrome.sidePanel.open({windowId: sender.tab.windowId});
        break;

      case 'is_this_tab_active':
        let {mess_id} = payload;

        let queryOptions = {active: true, lastFocusedWindow: true};
        chrome.tabs.query(queryOptions, ([tab]) => {
          if (tab) {
            sendResponse({
              is_active: (tab.id == sender.tab.id),
              mess_id: mess_id,
            });
          }
        });
        break;

      //  Request API to server

      case 'api_get_user_info':
        _Authorization_SW.getUserInfo(userInfo => {
          sendResponse(userInfo);
        });
        break;

      case 'api_domain_set_token_notification':
        _Authorization_SW.setTokenNotification(payload, result => {
          sendResponse(result);
        });
        break;

      case 'api_firebase_load_config':
        _Firebase_SW.loadConfig(config => {
          sendResponse(config);
        });
        break;

      case 'api_workflow_doc_create_request_check_content_email':
        _WorkflowDoc_SW.createRequestCheckContentEmail(payload, result => {
          sendResponse(result);
        });
        break;
    }

    return true;
  };

  /**
   * Initialize app
   *
   */
  const _initExt = () => {

    _Authorization_SW.getUserInfo(userLogin => {
      if (userLogin) {

        USER_ADDON_LOGIN = userLogin;
        EMAIL_USER_ADDON = userLogin.user_email;
        DOMAIN_USER_ADDON = userLogin.google_apps_domain;
        if (!DOMAIN_USER_ADDON) {
          let email = userLogin.user_email;
          DOMAIN_USER_ADDON = email.split('@')[1]
        }

        _Firebase_SW._init();
      }
    });

    chrome.tabs.create({
      active: true,
      url: "/sign-in.html"
    });

    chrome.sidePanel
      .setPanelBehavior({openPanelOnActionClick: true})
      .catch((error) => console.error(error));
  };

  chrome.runtime.onMessage.addListener(onMessageSW);
  chrome.runtime.onInstalled.addListener(_initExt);
  chrome.storage.onChanged.addListener(_Storage_SW.onChanged);
})();