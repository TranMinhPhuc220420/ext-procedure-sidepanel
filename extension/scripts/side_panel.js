(() => {
  FirebaseManager._init();

  const domain_path = 'vn2.sateraito.co.jp'.replaceAll('.', '__');
  $('#btn_send_test').on('click', () => {
    let id_email = MyUtils.randomId();
    let user_email = `${MyUtils.randomId()}@vn2.sateraito.co.jp`;

    let reference = FirebaseManager._database.ref(`${domain_path}/${id_email}`);
    reference.set({
      'id_email': MyUtils.randomId(),
      'user_email': user_email,
      'created_date': new Date(),
    });
  });

  setTimeout(() => {
    let reference_watch = FirebaseManager._database.ref(`${domain_path}`);
    reference_watch.on('value', (snapshot) => {
      const data = snapshot.val();
      console.log(data);

      $("#list_id_email_test").html('');

      for (const dataKey in data) {
        let testEl = document.createElement('div');
        testEl.innerHTML = `
          ID email: ${dataKey}
        `;
        $("#list_id_email_test").append(testEl)
      }
    });
  }, 1000)

})();