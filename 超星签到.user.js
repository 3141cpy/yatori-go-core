// ==UserScript==
// @name         超星签到
// @namespace    http://tampermonkey.net/
// @version      8.1
// @match        *://mobilelearn.chaoxing.com/*
// @require      https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js
// @grant        GM_addStyle
// ==/UserScript==
(function() {
    const $ = jQuery;
    GM_addStyle(`
    #signBox{position:fixed;right:14px;top:15px;width:350px;background:#fff;border:1px solid #ddd;padding:15px;z-index:99999999;border-radius:8px;box-shadow:0 0 10px #ccc;}
    .title{font-weight:bold;padding-bottom:8px;border-bottom:1px solid #eee;margin-bottom:10px;font-size:15px;}
    .item{margin:9px 0;}
    select{width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;}
    .loadBtn{width:100%;background:#26b855;color:#fff;border:none;padding:8px;border-radius:4px;cursor:pointer;}
    .submitBtn{width:100%;background:#e43838;color:#fff;border:none;padding:8px;border-radius:4px;margin-top:5px;cursor:pointer;}
    `);

    $('body').append(`
    <div id="signBox">
        <div class="title">签到状态修改工具</div>
        <div class="item"><button class="loadBtn" id="getList">①一键自动读取全部签到</button></div>
        <div class="item">
            <label>选择签到活动</label>
            <select id="activeSelect"><option>点击上方按钮加载数据</option></select>
        </div>
        <div class="item">
            <label>选择签到状态</label>
            <select id="statusSelect">
                <option value="1">已签</option>
                <option value="2">代签</option>
                <option value="4">请假</option>
                <option value="5">缺勤</option>
            </select>
        </div>
        <div class="item"><button class="submitBtn" id="sendEdit">②提交修改</button></div>
    </div>
    `);

    // 获取url参数
    function getParam(key){
        let sp = new URLSearchParams(location.search);
        return sp.get(key)||'';
    }

    // 一键拉取vm.activeList
    $("#getList").click(function(){
        try{
            let list = vm.activeList;
            let $select = $("#activeSelect");   // 获取select元素
            $select.empty();                    // 清空选项
            if(!list || !list.length){
                alert("暂无签到数据");
                return;
            }
            list.forEach(item=>{
                $select.append(`<option value="${item.activeid}">${item.name}【${item.activeid}】</option>`);
            });
            alert(`✅ 读取成功，共${list.length}条签到`);
        }catch(err){
            alert("读取失败：页面vm还未初始化，等待页面数据全部加载完再点");
            console.error(err);
        }
    });

    // 提交，剔除name参数
    $("#sendEdit").click(function(){
        let aid = $("#activeSelect").val();
        let status = $("#statusSelect").val();
        if(!aid) return alert("请先选择签到");
        $.get("/widget/sign/pcTeaSignController/updateSignStatus2",{
            uid:getParam("puid"),
            activeId:aid,
            status:status,
            denc:getParam("denc"),
            duid:getParam("duid")
        },res=>{
            if(res.result===1){
                alert("修改成功，页面刷新");
                location.reload();
            }else{
                alert("失败："+(res.errorMsg||"接口返回异常"));
            }
        }).fail(()=>alert("接口请求失败"));
    });
})();