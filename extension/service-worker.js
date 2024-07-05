import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.3/firebase-app.js";
import { getDatabase, ref, set, onValue } from "https://www.gstatic.com/firebasejs/10.12.3/firebase-database.js";

(() => {
  const firebaseConfig = {
    apiKey: "AIzaSyCFuEjuBomTlp_09Kre35FSzZgzUAeTFlI",
    authDomain: "pdsasf-50ce6.firebaseapp.com",
    databaseURL: "https://pdsasf-50ce6-default-rtdb.firebaseio.com",
    projectId: "pdsasf-50ce6",
    storageBucket: "pdsasf-50ce6.appspot.com",
    messagingSenderId: "639641619695",
    appId: "1:639641619695:web:fffd775cce7454547a1f1a",
    measurementId: "G-WTQXNPQECY",
  };


  // Initialize Firebase
  const app = initializeApp(firebaseConfig);

  // Initialize Realtime Database and get a reference to the service
  const database = getDatabase(app);

  let reference = ref(database, 'users/' + 'test_vn2_sateraito_co_jp')
  set(reference, {
    username: 'test vn2',
    email: 'test@vn2.sateraito.co.jp',
    profile_picture: 'none'
  });
  onValue(reference, (snapshot) => {
    console.log(snapshot);
    const data = snapshot.val();
    console.log(data);
  });

})();