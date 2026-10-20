package world.africandroid.africajobs;
import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.graphics.Bitmap;
import android.webkit.*;
import android.widget.*;
import android.view.View;

public class MainActivity extends Activity {
 private WebView web;
 private TextView status;
 private boolean internal(Uri u) { return "https".equals(u.getScheme()) && "jobs.africandroid.world".equalsIgnoreCase(u.getHost()) && u.getPort() == -1 && !u.getPath().toLowerCase(java.util.Locale.ROOT).endsWith(".apk"); }
 private void external(Uri u) {
  String s=u.getScheme();
  if (!("https".equals(s)||"mailto".equals(s)||"tel".equals(s)||"sms".equals(s))) return;
  try { startActivity(new Intent(Intent.ACTION_VIEW,u).addCategory(Intent.CATEGORY_BROWSABLE)); }
  catch (android.content.ActivityNotFoundException e) { status.setText("No app can open this link."); }
 }
 @Override public void onCreate(Bundle state) {
  super.onCreate(state);
  LinearLayout layout=new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL);
  LinearLayout bar=new LinearLayout(this);
  Button home=new Button(this); home.setText("Home"); home.setOnClickListener(new View.OnClickListener(){public void onClick(View v){web.loadUrl("https://jobs.africandroid.world/");}}); bar.addView(home);
  Button refresh=new Button(this); refresh.setText("Reload"); refresh.setOnClickListener(new View.OnClickListener(){public void onClick(View v){web.reload();}}); bar.addView(refresh);
  Button browser=new Button(this); browser.setText("Browser"); browser.setOnClickListener(new View.OnClickListener(){public void onClick(View v){external(Uri.parse("https://jobs.africandroid.world/"));}}); bar.addView(browser);
  layout.addView(bar); status=new TextView(this); status.setText("Development app • Internet required"); layout.addView(status);
  web=new WebView(this); layout.addView(web,new LinearLayout.LayoutParams(-1,0,1)); setContentView(layout);
  WebSettings s=web.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setAllowFileAccess(false); s.setAllowContentAccess(false); s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW); s.setGeolocationEnabled(false);
  CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
  web.setWebViewClient(new WebViewClient() {
   @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest r) { if(internal(r.getUrl())) return false; if(r.isForMainFrame()) external(r.getUrl()); return true; }
   @Override public void onPageStarted(WebView v,String url,Bitmap icon) {status.setText("Loading…");}
   @Override public void onPageFinished(WebView v,String url) {status.setText("Development app • "+"jobs.africandroid.world");}
   @Override public void onReceivedError(WebView v,WebResourceRequest r,WebResourceError e) {if(r.isForMainFrame()) status.setText("Connection failed. Check Internet and tap Reload.");}
   @Override public void onReceivedSslError(WebView v,android.webkit.SslErrorHandler h,android.net.http.SslError e) {h.cancel();status.setText("Secure connection failed. Certificate must be repaired on the website.");}
  });
  web.setDownloadListener(new DownloadListener(){public void onDownloadStart(String url,String ua,String cd,String mime,long length){external(Uri.parse(url));}});
  if(state!=null) web.restoreState(state); else web.loadUrl("https://jobs.africandroid.world/");
 }
 @Override protected void onSaveInstanceState(Bundle state) {web.saveState(state);super.onSaveInstanceState(state);}
 @Override public void onBackPressed() {if(web.canGoBack()) web.goBack();else super.onBackPressed();}
 @Override protected void onDestroy() {web.destroy();super.onDestroy();}
}
