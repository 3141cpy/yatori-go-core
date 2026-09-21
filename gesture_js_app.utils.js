(function(W, $, B) {
	
	if (typeof W.AppUtils != 'undefined') {
		return;
	}
	
	function AppUtils() {
	}
	
	/**
	 * 退出客户端
	 * 
	 * @param tips 退出时的提示信息
	 */
	AppUtils.prototype.exit = function(tips) {
		var cmd = 'CLIENT_EXIT_WEBAPP';
		
		B.postNotification(cmd, {
			message: tips || ''
		});
	};
	
	/**
	 * 退出当前webview
	 * 
	 * @param tips 退出时的提示信息
	 */
	AppUtils.prototype.closeView = function(tips) {
		var cmd = 'CLIENT_EXIT_LEVEL';
		
		B.postNotification(cmd, {
			message: tips || ''
		});
	};
	
	/**
	 * 打开语音识别
	 * 
	 * @param tips 打开语音识别时的提示信息
	 * @param callBack 接收语音识别回调方法
	 */
	AppUtils.prototype.openSpeech = function(tips, callBack) {
		var cmd = 'CLIENT_SPEECH_RECOGNIZER';
		
		B.unbind(cmd);
		
		callBack && B.bind(cmd, callBack);
		
		B.postNotification('CLIENT_SPEECH_RECOGNIZER', {
			message: tips || ''
		});
	};
	
	/**
	 * 打开条形码
	 * 
	 * @param tips 打开条形码时的提示信息
	 * @param callBack 条形码识别后的回调方法
	 */
	AppUtils.prototype.openScanner = function(tips, callBack) {
		var cmd = 'CLIENT_BARCODE_SCANNER';
		
		B.unbind(cmd);
		
		callBack && B.bind(cmd, callBack);
		
		B.postNotification(cmd, {
			manualInputTitle: tips || ''
		});
	};
	/**
	 * 打开视频播放器
	 * 
	 * @param option 可以是数组或一个object对象（视频信息）
	 */
	AppUtils.prototype.openVideoPlayer = function(option) {
		
		if ($.isEmptyObject(option)) {
			return;
		}
		
		var cmd = 'CLIENT_VIDEO_PLAYER';
		
		var defultOpt = {
			seriesid: 0, // 系列id
			title: '', // 视频标题
			videopathm3u8: '', // m3u8视频播放地址
			videopathmp4: '', // mp4播放地址
			candownload: 0 // 是否允许下载,默认不允许下载  (1可以下载，0不可下载)
		};
		
		var videos = new Array();
		
		if ($.isArray(option)) {
			for (var i = 0, o; o =  option[i++];) {
				if (!$.isEmptyObject(o)) {
					videos.push($.extend(defultOpt, o));
				}
			}
		} else {
			videos.push($.extend(defultOpt, option));
		}
		
		B.postNotification(cmd, {videolist: videos});
	};
	
	/**
	 * 打开图书
	 * 
	 * @param option 图书信息， obejct对象
	 */
	AppUtils.prototype.openBook = function(option) {
		
		if ($.isEmptyObject(option)) {
			return;
		}
		
		var cmd = 'CLIENT_READ_BOOK';
		
		B.postNotification(cmd, $.extend({
			type: 'pdz', // 图书类型， 默认是pdz
			uniqueID: '', // 唯一id, 这里是ssid
			remoteUrl: '', // 图书下载地址，book协议地址
			bookName: '', // 图书名
			message: '', // 信息
			coverUrl: '' // 封面地址
		}, option));
	};
	
	/**
	 * 下载图书
	 * 
	 * @param option 图书信息， obejct对象
	 */
	AppUtils.prototype.downloadBook = function(option) {
		
		if ($.isEmptyObject(option)) {
			return;
		}
		
		var cmd = 'CLIENT_DOWNLOAD_BOOK';
		
		B.postNotification(cmd, $.extend({
			type: 'pdz', // 图书类型， 默认是pdz
			uniqueID: '', // 唯一id, 这里是ssid
			remoteUrl: '', // 图书下载地址，book协议地址
			bookName: '', // 图书名
			message: '', // 信息
			coverUrl: '' // 封面地址
		}, option));
	};
	
	/**
	 * 定制菜单 (注：此方法必须放在 _jsBridgeReady方法中执行)
	 * 
	 * @param option 数组或obejct对象，菜单信息
	 */
	AppUtils.prototype.customMenu = function(option) {
		
		if ($.isEmptyObject(option)) {
			return;
		}
		
		var cmd = 'CLIENT_CUSTOM_MENU';
		
		B.postNotification(cmd, $.extend({
			index:0,
			show: 1, //是否显示  1显示，0不显示
			width:'',
			height:'',
			icon: '', //菜单图标，为空或没有此属性，则不显示
			menu: '', //菜单名称，为空或没有此属性，则不显示
			option: '', //操作，实际类型为js方法，在客户端上调用webapp内的js方法
			children: [] //为子菜单列表，如上述属性
		}, option));
	};
	
	
	/**
	 * 打开讨论组
	 * @param type  类型（专题类型值为3000）
	 * @param name 专题名称 
	 * @param sid  专题编号
	 * @param puid 生成小组时指定小组创建者为puid；如果不需要为空默认创建者为小星
	 */
	AppUtils.prototype.clientOpenGroup = function(type,name,sid,puid){
		
		var cmd = 'CLIENT_OPEN_GROUP';
		
		B.postNotification(cmd,{
			GroupInfo:{
				type:type,
				name:name,
				sid:sid,
				puid:puid
				}
		});
	};
	/**
	 * 获取登录状态
	 * 
	 * @param accountKey 账户类型的key, "" (空字符串)为统一认证用户信息, "cx_fanya"为泛雅用户信息， "cx_opac"为opac用户信息
	 * @param callback 获取登录状态的回调方法
	 */
	AppUtils.prototype.getLoginState =  function(accountKey, callback) {
		
		if (accountKey == null) {
			return;
		}
		
		var cmd = 'CLIENT_LOGIN_STATUS';
		
		B.unbind(cmd);
		
		callback && B.bind(cmd, callback);
		
		B.postNotification(cmd, {
			accountKey: accountKey
		});
	};
	
	/**
	 * 客户端打开链接地址，可以是webview或客户端浏览器, 默认使用webview打开，默认不检查是否登录
	 * 
	 * @param option object对象
	 */
	AppUtils.prototype.openUrl =  function(option) {
		
		if ($.isEmptyObject(option)) {
			return;
		}
		
		var cmd = 'CLIENT_OPEN_URL';
		
		if(/.*[\u4e00-\u9fa5]+.*$/.test(option.webUrl)){//有中文进行编码
			option.webUrl = encodeURI(option.webUrl);
		}
        if(option.webUrl.indexOf('/')==0){
        	option.webUrl = location.protocol+location.hostname+(location.port==80?"":(location.port+""))+option.webUrl;
        }
		B.postNotification(cmd, $.extend({
			title: '', //标题
			loadType: 1, //打开方式，0在本页面打开，1使用客户端webview打开新页面，2打开系统浏览器
			webUrl: '' //要打开的url
		}, option));
	};
	
	/**
	 * 分享
	 * 
	 * @param option object, 分享内容
	 */
	AppUtils.prototype.share = function(option) {
		
		if ($.isEmptyObject(option)) {
			return;
		}
		
		var cmd = 'CLIENT_SHARE_ITEM';
		
		B.postNotification(cmd, $.extend({
			url: '',  //网页地址
			imgUrl: '', //图片地址
			type:0, //类型，目前只有0表示网页
			title: '', //标题
			content: '' //文字描述
		}, option));
	};
	
	/**
	 * 获取书架图书
	 * 
	 * @param ids ids id 或 id数组
	 * @param callback 获取到图书后的回调方法
	 */
	AppUtils.prototype.getShelfBooks = function(ids, callback) {
		
		if (ids == null) {
			return;
		}
		
		var cmd = 'CLIENT_BOOKS_ON_SHELF';
		var bookIds = null;
		
		if ($.isArray(ids)) {
			bookIds = ids;
		} else {
			bookIds = new Array();
			bookIds.push(ids);
		}
		
		B.unbind(cmd);
		
		callback && B.bind(cmd, callback);
		
		B.postNotification(cmd, bookIds);
	};
	
	/**
	 * 打开图书详情
	 * 
	 * @param option object对象
	 */
	AppUtils.prototype.getBookDetail = function(option) {
		
		if ($.isEmptyObject(option)) {
			return;
		}
		
		var cmd = 'CLIENT_OPEN_BOOK_DETAIL';
		
		B.postNotification(cmd, $.extent({
			dxNumber: '', //图书读秀号
			d: '', //读秀加密串
			languageType: 0 //语言类型，0：中文，1:外文
		}, option));
	};
	
	/**
	 * 打开指定app
	 * 
	 * @param option object对象
	 */
	AppUtils.prototype.openApp = function(option) {
		
		if ($.isEmptyObject(option)) {
			return;
		}
		
		var cmd = 'CLIENT_OPEN_APP';
		
		B.postNotification(cmd, $.extent({
			appid: '', //应用id
			appname: '' //应用名称
		}, option));
	};
	
	/**
	 * 打开不同类型的资源管理器
	 * 
	 * @param type file:打开文件管理器, image:打开图库，相机, image_file：打开图库，相机，文件管理器
	 */
	AppUtils.prototype.openResourceMgr = function(type, callback) {
		
		if (typeof type == 'undefined') {
			return;
		}
		
		var cmd = 'CLIENT_FILEINPUTTYPE';
		
		B.unbind(cmd);
		
		callback && B.bind(cmd, callback);
		
		B.postNotification(cmd, {
			type: type
		});
	};
	
	/**
	 * 获取用户登录信息
	 * 
	 * @param accountKey 账户类型的key, "" (空字符串)为统一认证用户信息, "cx_fanya"为泛雅用户信息， "cx_opac"为opac用户信息
	 * @param callback 获取到用户信息的回调方法
	 */
	AppUtils.prototype.getUserInfo = function(accountKey, callback) {
		
		if (typeof accountKey == 'undefined') {
			return;
		}
		
		var cmd = 'CLIENT_GET_USERINFO';
		
		B.unbind(cmd);
		
		callback && B.bind(cmd, callback);
		
		B.postNotification(cmd, {
			accountKey: accountKey
		});
	};
	
	
	
	
	/**
	 * 调用客户端登录
	 * 
	 * @param accountKey 账户类型的key, "" (空字符串)为统一认证用户信息, "cx_fanya"为泛雅用户信息， "cx_opac"为opac用户信息
	 * @param callback 客户端登录后的回调方法
	 */
	AppUtils.prototype.doAppLogin = function(accountKey, callback) {
		
		if (typeof accountKey == 'undefined') {
			return;
		}
		
		var cmd = 'CLIENT_LOGIN';
		
		B.unbind(cmd);
		
		callback && B.bind(cmd, callback);
		
		B.postNotification(cmd, {
			accountKey: accountKey
		});
	};
	
	/**
	 * 调用手机通讯录，选择联系人
	 * 
	 * @param callback
	 */
	AppUtils.prototype.openContacts = function(callback) {
		
		var cmd = 'CLIENT_OPEN_CONTACTS';
		
		B.unbind(cmd);
		
		callback && B.bind(cmd, callback);
		
		B.postNotification(cmd);
	};
	/**
	 * 调用客户端消息提示
	 * @param message
	 */
	AppUtils.prototype.clientMessageDisplay = function(message){
		B.postNotification('CLIENT_DISPLAY_MESSAGE',{
			message: message
		});
	};
    /**
     * 根据passport用户id，调用客户端打开用户信息
     * @param message
     */
	AppUtils.prototype.clientOpenUserInfo = function(userId){
		B.postNotification('CLIENT_OPEN_USERINFO',{
			UserID: '',
			passportID:''+userId+''
		});
	};
    /**
     * 根据超星客户端用户id，调用客户端打开用户信息
     * @param message
     */
	AppUtils.prototype.clientOpenXXTUserInfo = function(userId){
		B.postNotification('CLIENT_OPEN_USERINFO',{
			UserID: ''+userId+'',
			passportID:''
		});
	};
	/**
	 * 转发
	 * @param content
	 * @param quoteInfo
	 */
	AppUtils.prototype.clientTransferInfo = function(content,quoteInfo) {
		B.postNotification('CLIENT_TRANSFER_INFO',{
			cataid: "100000001",
			content:content,
			quoteInfo:quoteInfo
//			docContent:docContent
		});
	};
	/**
	 * 发表话题
	 * @param circleId 小组id
	 * @param TopicId 话题id
	 * @param rights
	 */
	AppUtils.prototype.addBBSTopic = function(bbsid,circleId,TopicId,rights){
		var cmd = 'CLIENT_WRITE_TOPIC';
		B.postNotification(cmd, {
			Groupbbsid:bbsid,
			GroupId: circleId,
			TopicId:TopicId,
			rights:rights
		});
	};
	/**
	 * 打开话题详情
	 * @param bbsid
	 * @param circleId
	 * @param TopicId
	 * @param rights
	 */
	AppUtils.prototype.clientOpenTopicDieail = function(bbsid,circleId,rights,THIS){
		var TopicId = $(THIS).attr("_attr");
		var cmd = 'CLIENT_OPEN_TOPIC';
		B.postNotification(cmd, {
			Groupbbsid:bbsid,
			GroupId: circleId,
			TopicId:TopicId,
			rights:rights
		});
	}
    /**
     * 发通知
     * @param message
     */
	AppUtils.prototype.clientSendNotice = function(id,name) {
		var cmd = 'CLIENT_OPEN_SEND_NOTICE';
		B.postNotification(cmd,{
			subject: [{
				id:id,
				name:name
			}]
		});
	};
	
	/**
	 * 获取订阅状态
	 * @param appurl url地址
	 * @param callback 订阅状态回调方法
	 */
	AppUtils.prototype.getSubscribeState = function(appurl, callback) {
		
		if (typeof appurl == 'undefined') {
			return;
		}
		
		var cmd = 'CLIENT_APP_SUBSCRIPTION_STATUS';
		
		B.unbind(cmd);
		
		callback && B.bind(cmd, callback);
		
		B.postNotification(cmd, {
			appurl: appurl
		});
	};
    //CLIENT_RES_SUBSCRIPTION_STATUS
    /**
     * 获取资源订阅状态
     * @param appurl url地址
     * @param callback 订阅状态回调方法
     */
    AppUtils.prototype.getSubRssscribeState = function(cataid, cataName, key, callback) {
        
        var cmd = 'CLIENT_RES_SUBSCRIPTION_STATUS';
        
        B.unbind(cmd);
        
        callback && B.bind(cmd, callback);
        
        B.postNotification(cmd, {
        	"cataid":cataid,
        	"cataName":cataName,
        	"key":key
        });
    };
	/**
	 * 将网页订阅到首页
	 * 
	 * @param option object对象
	 */
	AppUtils.prototype.subscribe = function(option,callback) {
		if ($.isEmptyObject(option)) {
			return;
		}
		var cmd = 'CLIENT_SUBSCRIBE_APP';

		B.unbind(cmd);
		
		callback && B.bind(cmd, callback);
		
		B.postNotification(cmd, $.extend({
			appname: '', //订阅源名称
			loginId: 0, //认证类型，1、opac，2、passport，0、统一认证。默认为0
			appurl: '', //订阅源地址
			available: 1, //是否可用，10不可用，1可用，默认为1
			logoPath: '', //图标地址
			isWebapp: 1, //是否是webapp，1是，0不是，默认为1
			useClientTool: 2, //是否启用客户端工具条，1启用，0不自定义工具条，2，自定义分层结构的工具条，默认为1
			needLogin: 0, //是否需要登录，1需要，0不需要，默认为0
			needRegist: 0, //是否需要注册，1需要，0不需要，默认为0
			norder: 0, //排序值，默认为int最大值
			loginUrl: '', //登录认证地址
			properties: '', //登录提示语
			extendField: '', //扩展信息
			description: '', //说明信息
			usable: '', //是否可订阅的验证地址
			logoshowtype: 1, //首页图标显示方式：1、通用app显示方式，2、rss订阅源显示方式
			rights: 1, //订阅源权限，默认为1
			loginkey: '' //对应loginId相应的key值
		}, option));
	};
    
    /**
     * 资料市场订阅（报纸、Rss）
     * @param cataid
     * @param cataName
     * @param key
     * @param content
     * @param callback
     */
    AppUtils.prototype.recScribe = function(cataid, cataName, key, content, callback){
    	 var cmd = 'CLIENT_SUBSCRIBE_RES';
         B.unbind(cmd);
         callback && B.bind(cmd, callback);
    	 B.postNotification(cmd,{
    		 		cataid : cataid,
    		 		cataName :cataName,
    		 		key :key,
    		 		content :content
    		 	});
    };
    
    /**
     * 资料市场取消订阅（报纸、Rss）
     * @param cataid
     * @param cataName
     * @param key
     */
    AppUtils.prototype.cancelRecScribe = function(cataid, cataName, key, callback){
    	var cmd = 'CLIENT_REMOVE_RES';
        B.unbind(cmd);
        callback && B.bind(cmd, callback);
        B.postNotification(cmd,{
                cataid : cataid,
                cataName : cataName,
                key : key
        });
    };

    /**
     * rec订阅转发（报纸、网络阅读）转发
     * @param message
     */
    AppUtils.prototype.clientRecTransferInfo = function(cataid, content,quoteInfo) {
        B.postNotification('CLIENT_TRANSFER_INFO',{
            cataid: cataid,
            content:content,
            quoteInfo:quoteInfo
        });
    }
    
	W['AppUtils'] = new AppUtils();
})(window, jQuery, jsBridge);