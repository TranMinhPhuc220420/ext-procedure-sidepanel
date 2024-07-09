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
        "/third-party/firebase/firebase-app.js",
        "/third-party/firebase/firebase-database.js",
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

  const _Firebase_SW = {
    _init: () => {
      const self = _Firebase_SW;

      self.loadConfig(webappConfig => {
        if (typeof webappConfig == 'undefined') {
          console.warn('WEBAPP CONFIG FIREBASE IS ERROR')
          return;
        }

        self._config = webappConfig;

        // Initialize Firebase
        self._app = firebase.initializeApp(self._config);
        self._database = firebase.database();

        self.setRealTimeDB();
      });
    },

    onUserLoginChange: () => {
      const self = _Firebase_SW;

      if (USER_ADDON_LOGIN && !self._config) {
        self.loadConfig(webappConfig => {
          if (typeof webappConfig == 'undefined') {
            console.warn('WEBAPP CONFIG FIREBASE IS ERROR')
            return;
          }

          self._config = webappConfig;

          // Initialize Firebase
          self._app = firebase.initializeApp(self._config);
          self._database = firebase.database();

          self.setRealTimeDB();
        });
      }
    },

    loadConfig: (callback) => {
      _postRequest(`${SERVER_URL}/api/webapp/config`, {'config_get': 'firebase_config'}, (success, webappConfig) => {
        callback(success ? webappConfig : undefined);
      });
    },

    setRealTimeDB: () => {
      const self = _Firebase_SW;
      const domain_path = DOMAIN_USER_ADDON.replaceAll('.', '__')

      let reference = self._database.ref(`${domain_path}`);
      reference.on('value', (snapshot) => {
        console.log(snapshot);
        const data = snapshot.val();
        console.log(data);
      });
    },

    // other func for ext
    pushEmailRequestCheck: (id_email, params) => {
      const self = _Firebase_SW;
      const domain_path = DOMAIN_USER_ADDON.replaceAll('.', '__')

      let reference = self._database.ref(`${domain_path}/${id_email}`);
      reference.set(params);
    },
  };

  const _Storage_SW = {
    getUserLogin: (callback) => {
      chrome.storage.local.get('user_login', payload => {
        callback(payload.user_login)
      });
    },

    onChanged: (payload, type) => {
      if ('user_login' in payload) {
        let userLogin = payload['user_login'].newValue;

        if (userLogin) {
          USER_ADDON_LOGIN = userLogin;
          EMAIL_USER_ADDON = userLogin.user_email;
          DOMAIN_USER_ADDON = userLogin.google_apps_domain;
          if (!DOMAIN_USER_ADDON) {
            let email = userLogin.user_email;
            DOMAIN_USER_ADDON = email.split('@')[1]
          }
        } else {
          USER_ADDON_LOGIN = EMAIL_USER_ADDON = DOMAIN_USER_ADDON = undefined;
        }

        _Firebase_SW.onUserLoginChange();
      }
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

      case 'push_email_request_check':
        let {id_email} = payload;
        _Firebase_SW.pushEmailRequestCheck(id_email, payload);
        sendResponse(true);
        break;
    }

    return true;
  };

  /**
   * Initialize app
   *
   */
  const _initExt = () => {

    _Storage_SW.getUserLogin(userLogin => {
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