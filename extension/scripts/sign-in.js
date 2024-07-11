(() => {
  const idBtnWithGoogle = '#sign-in-with-google';

  // Func handler

  /**
   * Handler set permission notification
   *
   * @returns {Promise<void>}
   */
  const setNotification = async () => {
    await FirebaseManager._init();

    return await FirebaseManager.initMessaging(Authorization.info.user_email);
  };

  /**
   * Handler login success
   *
   * @param {string} message
   */
  const handlerSuccess = async (message) => {
    $(idBtnWithGoogle).addClass('login-success');


    let countDown = 3;
    $(idBtnWithGoogle).find('.text').html(`${message} (${countDown}s)`);

    try { // Initiate the browser prompt.
      const {success, msg, current_token} = await setNotification();
      console.log(current_token)
    } catch (err) {
      console.log(err)
      alert(chrome.i18n.getMessage('des_error_not_permission_notification') + err)
    }

    setInterval(() => {
      countDown -= 1;
      $('#sign-in-with-google .text').html(`${message} (${countDown}s)`);
      if (countDown <= 0) {
        window.close();
      }
    }, 1000);
  };

  /**
   * Handler login failed
   *
   */
  const handlerFailed = () => {
    $(idBtnWithGoogle).removeAttr('disabled', 'disabled');
    window.alert(chrome.i18n.getMessage('msg_login_failed'));
  };

  // Handler auto login
  $(idBtnWithGoogle).attr('disabled', 'disabled');
  $(idBtnWithGoogle).addClass('is-loading');
  Authorization.checkUserLogin(isLogged => {
    $(idBtnWithGoogle).attr('disabled', 'disabled');
    // $(idBtnWithGoogle).removeClass('is-loading');

    if (isLogged) {
      let message = chrome.i18n.getMessage('msg_welcome_back_after_auto_login')
      handlerSuccess(message);
    } else {
      $(idBtnWithGoogle).removeAttr('disabled', 'disabled');
      $(idBtnWithGoogle).removeClass('is-loading');
    }
  });

  // Set event submit login
  $(idBtnWithGoogle).click(event => {
    const btnEl = event.target;

    $(btnEl).attr('disabled', 'disabled');
    $(btnEl).addClass('is-loading');

    Authorization.handlerLogin(success => {
      $(btnEl).removeClass('is-loading');

      if (!success) {
        handlerFailed();
      } else {
        let message = chrome.i18n.getMessage('msg_login_success')
        handlerSuccess(message);
      }
    });
  });

  // Set languages for class "set-lang"
  const setLangEl = $('.set-lang');
  setLangEl.each((index, item) => {
    let key_lang = $(item).attr('msg');

    $(item).html(chrome.i18n.getMessage(key_lang) || key_lang)
  })
})();