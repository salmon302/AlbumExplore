

function popUpCommentReview(nrid) {
    oDivCommentReviewForm = document.getElementById("divCommentReviewForm" + nrid);
    oDivCommentReviewForm.style.display = 'block';
}


// Add to favorites fonction
function bookIt(argVal)
{
   var bookData = new Array();
   bookData = argVal.split("|");
   if (document.all)
      window.external.AddFavorite(bookData[0], bookData[1]);
   else
      alert("Sorry. Netscape users must bookmark the pages manually by hitting <Ctrl-D>");
}
function doSearch()
{
   var oQuery = document.getElementById("iQuery")
   if(oQuery.value != '' && oQuery.value.length >= 2)
    {
      window.document.location.href="search-results.asp?q="+oQuery.value
      //window.document.location.href="http://coveo.neomedia.com/progarchives/default.asp?q="+oQuery.value
     } 
}
function fnTrapKD(){
   if(event.keyCode == 13)
      doSearch()
   else
      event.returnValue=true;
}
function fcTrapFocus()
{
   var oQuery = document.getElementById("iQuery")
   if(oQuery.value != 'SEARCH')
      oQuery.value  = ''
}
function ValidContactForm()
{
    var strEmail = window.document.Fcontact.Iemail.value;
    
    if(window.document.Fcontact.Iname.value == "")
    {
        alert("Please enter your name");
        window.document.Fcontact.Iname.focus();
        return false;
    }
	 else if(strEmail.indexOf("@") == -1 || strEmail.indexOf(".") == -1)
	 {
		 alert("Please, provide a valid email adress");
		 window.document.Fcontact.Iemail.focus();
		 return false;
	 }
	 else if(window.document.Fcontact.Isubject.value == "")
	 {
		 alert("Please, provide a message subject");
		 window.document.Fcontact.Isubject.focus();
		 return false;
	 }
	 else if(window.document.Fcontact.Imessage.value == "")
	 {
		 alert("Please, provide a message");
		 window.document.Fcontact.Imessage.focus();
		 return false;
	 }
    else 
    {
       alert("Your message will be sent!\nYou will now be redirected to the ProgArchives home page.")
       return true;
    }
}

/****************************************************
*	        DOM Image rollover:
*		by Chris Poole
*		http://chrispoole.com
*               Script featured on http://www.dynamicdrive.com
*		Keep this notice intact to use it :-)
****************************************************/

function init() {
  if (!document.getElementById) return
  var imgOriginSrc;
  var imgTemp = new Array();
  var imgarr = document.getElementsByTagName('img');
  for (var i = 0; i < imgarr.length; i++) {
    if (imgarr[i].getAttribute('hsrc')) {
        imgTemp[i] = new Image();
        imgTemp[i].src = imgarr[i].getAttribute('hsrc');
        imgarr[i].onmouseover = function() {
            imgOriginSrc = this.getAttribute('src');
            this.setAttribute('src',this.getAttribute('hsrc'))
        }
        imgarr[i].onmouseout = function() {
            this.setAttribute('src',imgOriginSrc)
        }
    }
  }
}
//onload=init;


function showFullBio()
{
	oDivShort = document.getElementById("shortBio")
	oDivMore = document.getElementById("moreBio")
	oDivShort.style.display = 'none';
	oDivMore.style.display = 'block';
	
	oA = document.getElementById("aMoreLink")
	oA.style.display = 'none';
}

function handleCovers()
{
	if(document.getElementById("ishowcovers").checked == true)
	{
		createCookie('covers','1',365)
		//alert("cover=true")
	}
	else
	{
		createCookie('covers','0',365)
		//alert("cover=false")
	}
    
	window.document.location.href = window.document.location.href
		
}

//WORD and CARACTER counter for review
   var submitcount=0;
   function checkSubmit() {

      if (submitcount == 0)
      {
      submitcount++;
      document.Surv.submit();
      }
   }


function wordCounter(field) 
{
	wordcounter=0;
	
	for (x=0;x<field.value.length;x++) 
	{
      if (field.value.charAt(x) == " " && field.value.charAt(x-1) != " ")  
	  	wordcounter++
    }
	alert(wordcounter + " words")
	
}

function textCounter(field, countfield, maxlimit) {
  if (field.value.length > maxlimit)
      {field.value = field.value.substring(0, maxlimit);}
      else
      {countfield.value = maxlimit - field.value.length;}
  }
  


function createCookie(c_name,value,expiredays)
{
   var exdate=new Date();
   exdate.setDate(exdate.getDate()+expiredays);
   document.cookie=c_name+ "=" +escape(value)+
   ((expiredays==null) ? "" : ";expires="+exdate.toGMTString());
}

function readCookie(c_name)
{
   if (document.cookie.length>0)
     {
     c_start=document.cookie.indexOf(c_name + "=");
     if (c_start!=-1)
       { 
       c_start=c_start + c_name.length+1; 
       c_end=document.cookie.indexOf(";",c_start);
       if (c_end==-1) c_end=document.cookie.length;
       return unescape(document.cookie.substring(c_start,c_end));
       } 
     }
   return "";
}

function eraseCookie(name)
{
	createCookie(name,"",-1);
}
    
    
function openRatingForm()
{
   oDivRatingForm = document.getElementById("divRatings");
   oDivRatingForm.style.display = 'block';
   oSpanNoComments= document.getElementById("lblNoComments");
   if(oSpanNoComments)
      oSpanNoComments.style.display = 'none';
   document.getElementById("icomment").focus();
}


function echeck(str) 
{
    
    var at="@"
    var dot="."
    var lat=str.indexOf(at)
    var lstr=str.length
    var ldot=str.indexOf(dot)
    if (str.indexOf(at)==-1){
     alert("Invalid E-mail ID")
     return false
    }
    
    if (str.indexOf(at)==-1 || str.indexOf(at)==0 || str.indexOf(at)==lstr){
     alert("Invalid E-mail ID")
     return false
    }
    
    if (str.indexOf(dot)==-1 || str.indexOf(dot)==0 || str.indexOf(dot)==lstr){
      alert("Invalid E-mail ID")
      return false
    }
    
    if (str.indexOf(at,(lat+1))!=-1){
      alert("Invalid E-mail ID")
      return false
    }
    
    if (str.substring(lat-1,lat)==dot || str.substring(lat+1,lat+2)==dot){
      alert("Invalid E-mail ID")
      return false
    }
    
    if (str.indexOf(dot,(lat+2))==-1){
      alert("Invalid E-mail ID")
      return false
    }
    
    if (str.indexOf(" ")!=-1){
      alert("Invalid E-mail ID")
      return false
    }
    
    return true					
}


function ValidForm()
{
   oForm = document.getElementById("Frateit");
   oRadioRating = document.getElementById("hRateValue");
   oChkGuidelines = document.getElementById("IacceptRules");

   if(oRadioRating.value != '' & oChkGuidelines.checked == true)
   {
	  oForm.submit();
	  return true;
   }
   else
   {
      alert('You must enter your ratings and read and check the guidelines.\nThank You');
      return false;
   }
}
function OpenGuidelines()
{
   oDivRatingForm = document.getElementById("divGuidelines");
   oDivRatingForm.style.display = 'block';
}

function checkFiveStars()
{
   alert('\nPROG ARCHIVES REVIEWS GUIDELINES WARNING\n\n\nBefore assigning a star rating to an album, you should carefully consider what the differing numbers of stars stand for.Please use "one" and "five star" ratings very sparingly -- most albums you dislike will have at least some positive qualities, and not every album that you enjoy will be a perfect "masterpiece."');
}

function openPopup(url, width, height) {

    width = eval(width);
    height = eval(height + 50) + 120; //+130 for extra space needed by adsense ads + 70 logo
    
    y = (screen.availHeight - height)/2;
    x = (screen.availWidth - width)/2;
        
    window.open(url, "", "width="+width+",height="+height+",location=no,menubar=no,resizable=no,scrollbars=no,status=no,titlebar=yes,toolbar=no,screenX="+x+",screenY="+y+",top="+y+",left="+x);
}

function slideShow() {

	//Set the opacity of all images to 0
	$('#gallery a').css({opacity: 0.0});
	
	//Get the first image and display it (set it to full opacity)
	$('#gallery a:first').css({opacity: 1.0});
	
	//Set the caption background to semi-transparent
	//$('#gallery .caption').css({opacity: 0.7});

	//Resize the width of the caption according to the image width
	//$('#gallery .caption').css({width: $('#gallery a').find('img').css('width')});
	
	//Get the caption of the first image from REL attribute and display it
	$('#gallery .content').html($('#gallery a:first').find('img').attr('rel'))
	.animate({opacity: 0.7}, 400);
	
	//Call the gallery function to run the slideshow, 6000 = change to next image after 6 seconds
	setInterval('gallery()',6000);
	
}

function gallery() {
	
	//if no IMGs have the show class, grab the first image
	var current = ($('#gallery a.show')?  $('#gallery a.show') : $('#gallery a:first'));

	//Get next image, if it reached the end of the slideshow, rotate it back to the first image
	var next = ((current.next().length) ? ((current.next().hasClass('caption'))? $('#gallery a:first') :current.next()) : $('#gallery a:first'));	
	
	//Get next image caption
	//var caption = next.find('img').attr('rel');	
	
	//Set the fade in effect for the next image, show class has higher z-index
	next.css({opacity: 0.0})
	.addClass('show')
	.animate({opacity: 1.0}, 1000);

	//Hide the current image
	current.animate({opacity: 0.0}, 1000)
	.removeClass('show');
	
	//Set the opacity to 0 and height to 1px
	//$('#gallery .caption').animate({opacity: 0.0}, { queue:false, duration:0 }).animate({height: '1px'}, { queue:true, duration:300 });	
	
	//Animate the caption, opacity to 0.7 and heigth to 100px, a slide up effect
	//$('#gallery .caption').animate({opacity: 0.7},100 ).animate({height: '100px'},500 );
	
	//Display the content
	$('#gallery .content').html(caption);
	
}
