$(document).ready(function() {
	try{
		var oTopBtn = document.getElementById('to_top');
	    var p=$(window.document.body);
	    var h = $(window.document.head);
	    
		if ($('.floatLayer', document).length > 0) {
	        $('.floatLayer', document).remove();
	    }
	    var style = document.createElement("style");
	    style.type = "text/css";
	    style.innerHTML=".floatLayer {position: fixed;z-index: 9;right: 0px;display: block;width: 132px;}\n" +
	        ".floatLayer a {display: block;width: 132px;height: 50px;line-height: 50px;margin-bottom: 20px;font-size: 16px;color: #3A8BFF;background: #ffffff;border-radius: 32px;-webkit-box-shadow: 0px 2px 10px 0px rgba(31, 35, 41, 0.1);box-shadow: 0px 2px 10px 0px rgba(31, 35, 41, 0.1);}\n" +
			".floatLayer a img {float: left;margin: 13px 8px 13px 18px; width: 24px;height: 24px;}\n" +
	        ".floatLayer a:hover img, .floatLayer a:hover span {opacity: 0.7;}\n"
	    h.append(style);
	    p.append(oTopBtn);
	    if(oTopBtn){
	        $(oTopBtn).css("display","hidden");
	    }
	    var top1= $('#goTop', document);
	    var  backToTopFun = function() {
	        try {
	            var st = $(top.document).scrollTop();
	            (st > 0)? top1.show(): top1.hide();
	        } catch (e) {
	
	        }
	
	
	    };
	    $(document).bind("scroll", backToTopFun);
	}catch(e){
		
	}
});