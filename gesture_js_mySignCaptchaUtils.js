var mySignCaptchaUtils = {
    INSTANCE: null,
    INIT_STATUS: 0,
    SAFE_POPUP_COUNT: 0,
    POPUP_TIMEOUT_HANDLER: null,
    VALIDATE_FAIL_COUNT: 0,
    VALIDATE_CODE_STR: "",
    verifySuccessCallback: null,
    CAPTCHA_TYPE: "slide",

    initSignCaptchaPlugin: function () {
        mySignCaptchaUtils.INIT_STATUS = 1;
        initCXCaptcha({
            captchaId: 'Qt9FIw9o4pwRjOyqM6yizZBh682qN2TU',
            element: '#captcha',
            mode: 'popup',
            type: mySignCaptchaUtils.CAPTCHA_TYPE,
            onVerify: function (err, data) {
                /**
                 * 第一个参数是err（Error的实例），验证失败才有err对象
                 * 第二个参数是data对象，验证成功后的相关信息，data数据结构为key-value，如下：
                 * {
                 * validate: 'xxxxx' // 二次验证信息
                 * }
                 **/
                if (err) {
                    mySignCaptchaUtils.VALIDATE_FAIL_COUNT++;
                    if (mySignCaptchaUtils.VALIDATE_FAIL_COUNT >= 4) {
                        jsBridge.postNotification('CLIENT_DISPLAY_MESSAGE', {'message':"验证次数过多"});
                        jsBridge.postNotification('CLIENT_EXIT_LEVEL', {}) ;
                    }
                    return; // 当验证失败时，内部会自动refresh方法，无需手动再调用一次
                }
                mySignCaptchaUtils.VALIDATE_CODE_STR = data.validate;
                mySignCaptchaUtils.verifySuccessCallback && mySignCaptchaUtils.verifySuccessCallback(data.validate);
                mySignCaptchaUtils.INSTANCE.refresh();
            }
        }, function onload(instance) {
            mySignCaptchaUtils.INSTANCE = instance;
            mySignCaptchaUtils.INIT_STATUS = 2;
        }, function onerror(err) {
            mySignCaptchaUtils.INIT_STATUS = -1;
        });
    },

    popUpCaptcha: function () {
        mySignCaptchaUtils.SAFE_POPUP_COUNT++;
        if (mySignCaptchaUtils.SAFE_POPUP_COUNT > 10) {
            jsBridge.postNotification('CLIENT_DISPLAY_MESSAGE', {'message':"签到验证码加载异常，请重新进入签到"});
            jsBridge.postNotification('CLIENT_EXIT_LEVEL', {}) ;
            return;
        }
        switch (mySignCaptchaUtils.INIT_STATUS) {
            case -1:
                jsBridge.postNotification('CLIENT_DISPLAY_MESSAGE', {'message':"验证码加载失败，请重新进入签到"});
                jsBridge.postNotification('CLIENT_EXIT_LEVEL', {}) ;
                break;
            case 0:
                mySignCaptchaUtils.initSignCaptchaPlugin();
                mySignCaptchaUtils.POPUP_TIMEOUT_HANDLER = setTimeout(mySignCaptchaUtils.popUpCaptcha, 500);
                break;
            case 1:
                mySignCaptchaUtils.POPUP_TIMEOUT_HANDLER = setTimeout(mySignCaptchaUtils.popUpCaptcha, 500);
                break;
            case 2:
                mySignCaptchaUtils.INSTANCE && mySignCaptchaUtils.INSTANCE.popUp();
                break;
            default:
                jsBridge.postNotification('CLIENT_DISPLAY_MESSAGE', {'message':"未知错误，请重新进入页面"});
                jsBridge.postNotification('CLIENT_EXIT_LEVEL', {}) ;
                break;
        }
    },
    
    setCaptchaType: function (type) {
        if (!type) {
            return;
        }
        switch (type) {
            case 1: // 滑块验证码
                mySignCaptchaUtils.CAPTCHA_TYPE = "slide";
                break;
            case 2: // 点击文字
                mySignCaptchaUtils.CAPTCHA_TYPE = "textclick";
                break;
            case 3: // 旋转图片
                mySignCaptchaUtils.CAPTCHA_TYPE = "rotate";
                break;
            case 4: // 点击图案
                mySignCaptchaUtils.CAPTCHA_TYPE = "iconclick";
                break;
            case 5: // 躲避障碍
                mySignCaptchaUtils.CAPTCHA_TYPE = "obstacle";
                break;
            default:
                mySignCaptchaUtils.CAPTCHA_TYPE = "slide";
                return;
        }
    }
}
