/** @define {object} GLOBALS_GMAIL*/
let GLOBALS_GMAIL = null;

//==========CREATE HANDLE TO GET [GLOBALS] VARIABLE GMAIL=================
//CREATE HANDLE TO GET [GLOBALS] VARIABLE GMAIL
let s = document.createElement("script");
s.src = chrome.runtime.getURL("scripts/script.js");
(document.head || document.documentElement).appendChild(s);
s.onload = function () {
  s.remove();
};

// Event listener
document.addEventListener("RW759_connectExtension", function (e) {
  // e.detail contains the transferred data (can be anything, ranging
  // from JavaScript objects to strings).
  // Do something, for example:
  if (typeof e.detail != "undefined") {
    GLOBALS_GMAIL = e.detail;
  }
});
//=============================END HANDLE===================================

(() => {
  "use strict";

  // ==== main ====
  let FAVICON_URL = chrome.runtime.getURL("images/favicon.png");

  let BTN_EXT_PROCEDURE_ID = "SATERAITO_EXT_PROCEDURE";
  let BTN_BBAR_EXT_PROCEDURE_CLS = "bbar-sateraito-ext-procedure";

  let FoDoc;
  let FBoolMail;

  const getCurrentUser = () => {
    var current_user = "";
    if (GLOBALS_GMAIL != null) {
      if (typeof GLOBALS_GMAIL != "undefined") {
        if (GLOBALS_GMAIL.length > 10) {
          current_user = GLOBALS_GMAIL[10];
          if (typeof current_user == "undefined") current_user = "";
        }
      }
    }
    return current_user;
  };

  const isContentTabActive = (callback) => {
    let messId = MyUtils.randomId();

    chrome.runtime.sendMessage({method: 'is_this_tab_active', payload: {mess_id: messId}}, (res) => {
      callback(res.is_active && messId == res.mess_id);
    });
  };

  /**
   * Handler when storage has value change
   *
   * @param {object} payload
   * @param {object} type
   */
  const storageOnChanged = (payload, type) => {
  };

  const Mail_ExtProcedure = {
    detectInterval_100: null,

    _init: () => {
      let self = Mail_ExtProcedure;
      if (self.detectInterval_100 != null) {
        clearInterval(self.detectInterval_100);
      }
      self.detectInterval_100 = setInterval(self.handleDetect, 200);

      // self.resetEvent();
    },

    // Process func

    /**
     * Process add button to bottom bar for all box reply mail
     *
     */
    processAddBtnForListBoxReply: function () {
      let self = Mail_ExtProcedure;
      let lisBBarReplyEl = FoDoc.querySelectorAll(".G3.G2 .IZ .btC");

      for (let i = 0; i < lisBBarReplyEl.length; i++) {
        let itemBBarEl = lisBBarReplyEl[i];

        if (itemBBarEl.querySelector(`.${BTN_BBAR_EXT_PROCEDURE_CLS}`)) continue;

        let elmBtn = document.createElement("div");
        elmBtn.addEventListener("click", self.handlerBBarBtnClick);
        elmBtn.setAttribute("data-tooltip", MyLang.getMsg("TXT_AI_REPLY"));
        elmBtn.setAttribute("data-label", MyLang.getMsg("TXT_AI_REPLY"));
        elmBtn.setAttribute("role_btn", "reply");
        elmBtn.className = BTN_BBAR_EXT_PROCEDURE_CLS + " wG J-Z-I";

        let vHtml = `
          <img style="pointer-events:none" src="${FAVICON_URL}">
          `;

        elmBtn.innerHTML = vHtml;

        if (itemBBarEl.querySelector(".gU .bAK")) {
          itemBBarEl.querySelector(".gU .bAK").append(elmBtn);
        } else if (itemBBarEl.querySelector(".gU.aYL")) {
          itemBBarEl.insertBefore(elmBtn, itemBBarEl.querySelector(".gU.aYL"));
        } else if (itemBBarEl.querySelector(".gU.a0z")) {
          itemBBarEl.insertBefore(elmBtn, itemBBarEl.querySelector(".gU.a0z"));
        } else {
          itemBBarEl.append(elmBtn);
        }
      }
    },

    /**
     * Process add button to bottom bar and menu for all box compose mail
     *
     */
    processAddBtnForListBoxCompose: function () {
      let self = Mail_ExtProcedure;

      // process for add button to bottom bar
      let lisBBarComposeEl = FoDoc.querySelectorAll(".nH .aaZ .btC");
      for (let i = 0; i < lisBBarComposeEl.length; i++) {
        let itemBBarEl = lisBBarComposeEl[i];

        if (itemBBarEl.querySelector(`.${BTN_BBAR_EXT_PROCEDURE_CLS}`)) continue;

        let elmBtn = document.createElement("div");
        elmBtn.addEventListener("click", self.handlerBBarBtnClick);
        elmBtn.setAttribute("data-tooltip", MyLang.getMsg("TXT_AI_REPLY"));
        elmBtn.setAttribute("data-label", MyLang.getMsg("TXT_AI_REPLY"));

        let is_really_compose =
          $(itemBBarEl)
            .parents(".AD")
            .find('.aoP .I5 .bAs table[role="presentation"]').length == 0;
        elmBtn.setAttribute(
          "role_btn",
          is_really_compose ? "compose" : "reply"
        );

        elmBtn.className = BTN_BBAR_EXT_PROCEDURE_CLS + " wG J-Z-I";

        let vHtml = `
          <img style="pointer-events:none" src="${FAVICON_URL}">
          `;

        elmBtn.innerHTML = vHtml;

        if (itemBBarEl.querySelector(".gU .bAK")) {
          itemBBarEl.querySelector(".gU .bAK").append(elmBtn);
        } else if (itemBBarEl.querySelector(".gU.aYL")) {
          itemBBarEl.insertBefore(elmBtn, itemBBarEl.querySelector(".gU.aYL"));
        } else if (itemBBarEl.querySelector(".gU.a0z")) {
          itemBBarEl.insertBefore(elmBtn, itemBBarEl.querySelector(".gU.a0z"));
        } else {
          itemBBarEl.append(elmBtn);
        }
      }

      // process for add button to menu bar
      let lisMenuReplyEl = FoDoc.querySelectorAll(".J-M.Gj.jQjAxd .SK.AX");
      for (let i = 0; i < lisMenuReplyEl.length; i++) {
        let itemBBarEl = lisMenuReplyEl[i];

        if (itemBBarEl.querySelector(`.${BTN_BBAR_EXT_PROCEDURE_CLS}`)) continue;

        let elmBtn = document.createElement("div");
        elmBtn.addEventListener("click", self.handlerBBarBtnClick);

        let is_really_reply =
          $(itemBBarEl)
            .parents(".M9")
            .find('.aoP .I5 .bAs table[role="presentation"]').length > 0;
        elmBtn.setAttribute("role_btn", is_really_reply ? "reply" : "compose");

        elmBtn.className = BTN_BBAR_EXT_PROCEDURE_CLS + " J-N";

        let vHtml = `
            <div class="J-N-Jz">
              <img class="nF-aMA-ato-Kp-JX J-N-JX" src="${FAVICON_URL}">
              ${MyLang.getMsg("TXT_AI_REPLY")}
            </div>
          `;
        elmBtn.innerHTML = vHtml;

        itemBBarEl.append(elmBtn);
      }
    },

    // Handler func

    /**
     * Handler detect add-on when running in mail
     *
     */
    handleDetect: function () {
      let self = Mail_ExtProcedure;

      // Render button AI reply for all box reply
      self.processAddBtnForListBoxReply();

      // Render button AI reply for all box compose
      self.processAddBtnForListBoxCompose();
    },

    /**
     * handlerBBarBtnClick
     *
     * @param event
     */
    handlerBBarBtnClick: function (event) {
      let btnEl = event.target;

      let containerBox = $(btnEl).parents('.nH.Hd')
      let idDraftRaw = $(containerBox).find('form.bAs input[name="draft"]').val();
      let idDraft = idDraftRaw.split(':')[1];

      FirebaseManager.addRequestCheckMailToAdmin(getCurrentUser(), idDraft);
    }
  };

  /**
   * Initialize add on
   *
   */
  function initialize() {
    MyUtils.debugLog("▼▼▼ initialize started ! ");

    let strUrl = document.URL;
    if (window === window.top) {
      FoDoc = document;

      FBoolMail = strUrl.indexOf("//mail.google.com/") >= 0;
      if (FBoolMail) {
        Authorization.getUserInfo(userInfo => {
          if (userInfo) {
            if (userInfo.user_email != getCurrentUser()) {
              alert("Ext Sateraito Warning: Email does not match the logged in email");
              return;
            }

            FirebaseManager._init();

            Mail_ExtProcedure._init();

            chrome.storage.onChanged.addListener(storageOnChanged);
          }
        });
      }

      $(document).on("click", (event) => {

      });
    }
  }

  // __main__
  const interval_important_for_init = setInterval(() => {
    if (getCurrentUser() != "") {

      // Start initialize
      initialize();

      clearInterval(interval_important_for_init);
    }
  }, 100);
})();