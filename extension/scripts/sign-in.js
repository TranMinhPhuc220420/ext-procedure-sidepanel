(() => {
  const idBtnWithGoogle = '#sign-in-with-google';

  const handlerSuccess = async (message) => {
    $(idBtnWithGoogle).addClass('login-success');

    try { // Initiate the browser prompt.
      const res = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    } catch (err) {
      alert(chrome.i18n.getMessage('des_error_not_permission_microphone'))
    }

    $(idBtnWithGoogle).find('.text').html(`${message} (3s)`);
    let countDown = 3;
    setInterval(() => {
      countDown -= 1;
      $('#sign-in-with-google .text').html(`${message} (${countDown}s)`);
      if (countDown <= 0) {
        window.close();
      }
    }, 1000);
  };
  const handlerFailed = () => {
    $(idBtnWithGoogle).removeAttr('disabled', 'disabled');
    window.alert(chrome.i18n.getMessage('msg_login_failed'));
  };

  $(idBtnWithGoogle).click(event => {
    const btnEl = event.target;

    $(btnEl).attr('disabled', 'disabled');
    $(btnEl).addClass('is-loading');

    Authorization.handlerLogin(accessToken => {
      $(btnEl).removeClass('is-loading');

      if (!accessToken) {
        handlerFailed();
      } else {
        let message = chrome.i18n.getMessage('msg_login_success')
        handlerSuccess(message);
      }
    });
  });

  Authorization.checkUserLogin(isLogged => {
    $(idBtnWithGoogle).attr('disabled', 'disabled');

    if (isLogged) {
      let message = chrome.i18n.getMessage('msg_welcome_back_after_auto_login')
      handlerSuccess(message);
    } else {
      $(idBtnWithGoogle).removeAttr('disabled', 'disabled');
      $(idBtnWithGoogle).removeClass('is-loading');
    }
  });

  // Set languages for class "set-lang"
  const setLangEl = $('.set-lang');
  setLangEl.each((index, item) => {
    let key_lang = $(item).attr('msg');
    
    $(item).html(chrome.i18n.getMessage(key_lang) || key_lang)
  })
})();