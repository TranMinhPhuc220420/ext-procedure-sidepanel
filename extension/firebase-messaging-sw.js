importScripts('/third-party/firebase-10.12.3/firebase-app-compat.js');
importScripts('/third-party/firebase-10.12.3/firebase-messaging-compat.js');

const SERVER_URL = 'https://ext2005-dot-vn-sateraito-apps-fileserver2.appspot.com';

const loadConfig = () => {
  const data = {'config_get': 'firebase_config'};

  return new Promise((resolve, reject) => {
    // Action call request
    fetch(`${SERVER_URL}/api/webapp/config`,
      {
        method: 'POST',
        headers: {},
        body: JSON.stringify(data)
      })

      // handler for response success
      .then(async dataRes => {
        let jsonData = await dataRes.json();

        if ('status' in jsonData) {
          if (jsonData['status'] != 'ok') {
            return reject(jsonData['status']);
          }
        }

        let data = jsonData;
        if ('data' in jsonData) {
          data = jsonData['data'];
          return resolve(data);
        }
      })

      // handler for request or response is error
      .catch(error => {
        return reject(error);
      })
  })
};
const init_message_sw = async () => {
  // const conf = await loadConfig();
  const conf = {
    "apiKey": "AIzaSyCFuEjuBomTlp_09Kre35FSzZgzUAeTFlI",
    "authDomain": "pdsasf-50ce6.firebaseapp.com",
    "databaseURL": "https://pdsasf-50ce6-default-rtdb.firebaseio.com",
    "projectId": "pdsasf-50ce6",
    "storageBucket": "pdsasf-50ce6.appspot.com",
    "messagingSenderId": "639641619695",
    "appId": "1:639641619695:web:fffd775cce7454547a1f1a",
    "measurementId": "G-WTQXNPQECY",
    "vapidKey": "BLyRTnCWp_0fUxM_f6iz6PTZTVQOu4yW0o6wz9ryAYvaPQVhLelzFY_7dJak-9QG_Qq0M7TnNyzKu35UbhhipHc",
  };

  const _app = await firebase.initializeApp(conf);
  const _messaging = await firebase.messaging();

  _messaging.onBackgroundMessage((payload) => {
    console.log('[firebase-messaging-sw.js] Received background message', payload);
  });
};

const handlerOpenWindowToOpenSidePanel = (event, action, data) => {
  event.waitUntil(clients.openWindow(`/ext-page.html?action=${action}`));
}

self.addEventListener('notificationclick', function (event) {
  console.log('[firebase-messaging-sw.js] notificationclick', event);

  let {
    action, notification
  } = event;

  if (!action || action == '') {
    action = 'action_detail';
  }
  if (!notification.data) {
    return;
  }
  if (!notification.data['FCM_MSG']) {
    return;
  }

  switch (action) {

    case 'action_detail':
      handlerOpenWindowToOpenSidePanel(event, action, notification.data['FCM_MSG'].data);
      break;

    case 'action_allow':
      break;

    case 'action_block':
      break;

    default:
      console.error(`Unknown action name="${action}"`);
  }
});

init_message_sw();