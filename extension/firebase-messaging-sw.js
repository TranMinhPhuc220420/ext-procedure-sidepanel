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
  const conf = await loadConfig();

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