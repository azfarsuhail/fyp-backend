# Android Deep Linking Guide for Password Reset

## Overview
This guide explains how to configure your Android app to receive password reset links via deep linking using Android App Links.

---

## 1. Android App Links Configuration

### Add to `AndroidManifest.xml`

Add the following intent filter to your activity that handles password reset:

```xml
<activity
    android:name=".ResetPasswordActivity"
    android:exported="true">
    
    <!-- Android App Links for password reset -->
    <intent-filter android:autoVerify="true">
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        
        <!-- Accepts URIs that begin with "https://kneeoa.online/reset-password" -->
        <data android:scheme="https" 
              android:host="kneeoa.online" 
              android:pathPrefix="/reset-password" />
    </intent-filter>
    
</activity>
```

### Alternative: Add to Existing Activity

If you want to handle password reset in your existing main activity:

```xml
<activity
    android:name=".MainActivity"
    android:exported="true">
    
    <!-- Existing intent filters -->
    
    <!-- Add this for password reset -->
    <intent-filter android:autoVerify="true">
        <action android:name="android.intent.action.VIEW" />
        <category android:name="android.intent.category.DEFAULT" />
        <category android:name="android.intent.category.BROWSABLE" />
        
        <data android:scheme="https" 
              android:host="kneeoa.online" 
              android:pathPrefix="/reset-password" />
    </intent-filter>
    
</activity>
```

---

## 2. Verify App Links Assertion

### Download assetlinks.json

Your backend serves the verification file at:
```
https://kneeoa.online/.well-known/assetlinks.json
```

**Expected Content:**
```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.azfarsuhail.kneeoaapp",
      "sha256_cert_fingerprints": [
        "93:1A:94:70:8D:C3:EB:8B:67:64:E9:64:54:34:28:1E:7D:66:7A:60:27:8E:1E:D4:1E:0E:5E:FA:1C:79:AE:A5"
      ]
    }
  }
]
```

### Verify in Android Studio

1. Open **Build** menu
2. Select **Analyze APK...**
3. Select your APK file
4. Click **App Links** tab
5. Verify that `kneeoa.online` is listed

### Verify via Command Line

```bash
adb shell appops set com.azfarsuhail.kneeoaandroid APP_TO_INSTALL allow
adb install --bypass-low-target-sdk-block your-app.apk
adb shell appops set com.azfarsuhail.kneeoaandroid APP_TO_INSTALL ignore
```

---

## 3. Handle Deep Link in Code

### Kotlin Implementation

```kotlin
class ResetPasswordActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Handle incoming intent
        handleIntent(intent)
        
        // Also handle if activity is already running
        if (intent.action == Intent.ACTION_VIEW) {
            intent.data?.let { uri ->
                extractTokenFromUri(uri)
            }
        }
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }
    
    private fun handleIntent(intent: Intent) {
        if (intent.action == Intent.ACTION_VIEW) {
            intent.data?.let { uri ->
                extractTokenFromUri(uri)
            }
        }
    }
    
    private fun extractTokenFromUri(uri: Uri) {
        // Extract token from query parameter
        val token = uri.getQueryParameter("token")
        
        if (!token.isNullOrEmpty()) {
            // Navigate to password reset screen
            showResetPasswordScreen(token)
        } else {
            showError("Invalid reset link")
        }
    }
    
    private fun showResetPasswordScreen(token: String) {
        // Navigate to your password reset UI
        val fragment = ResetPasswordFragment().apply {
            arguments = bundleOf("reset_token" to token)
        }
        
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragment_container, fragment)
            .addToBackStack(null)
            .commit()
    }
}
```

### Java Implementation

```java
public class ResetPasswordActivity extends AppCompatActivity {
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        handleIntent(getIntent());
    }
    
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }
    
    private void handleIntent(Intent intent) {
        if (Intent.ACTION_VIEW.equals(intent.getAction())) {
            Uri uri = intent.getData();
            if (uri != null) {
                String token = uri.getQueryParameter("token");
                
                if (!TextUtils.isEmpty(token)) {
                    showResetPasswordScreen(token);
                } else {
                    showError("Invalid reset link");
                }
            }
        }
    }
    
    private void showResetPasswordScreen(String token) {
        ResetPasswordFragment fragment = new ResetPasswordFragment();
        Bundle args = new Bundle();
        args.putString("reset_token", token);
        fragment.setArguments(args);
        
        getSupportFragmentManager().beginTransaction()
            .replace(R.id.fragment_container, fragment)
            .addToBackStack(null)
            .commit();
    }
}
```

---

## 4. Fragment Implementation

```kotlin
class ResetPasswordFragment : Fragment() {
    
    private lateinit var binding: FragmentResetPasswordBinding
    private var resetToken: String? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        resetToken = arguments?.getString("reset_token")
    }
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        binding = FragmentResetPasswordBinding.inflate(inflater, container, false)
        return binding.root
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        resetToken?.let { token ->
            // Show loading state
            binding.progressBar.visibility = View.VISIBLE
            
            // Validate token with backend
            validateAndResetPassword(token)
        } ?: run {
            showError("Invalid reset link")
        }
    }
    
    private fun validateAndResetPassword(token: String) {
        // Get password inputs
        val newPassword = binding.newPasswordEditText.text.toString()
        val confirmPassword = binding.confirmPasswordEditText.text.toString()
        
        // Validate passwords match
        if (newPassword != confirmPassword) {
            showError("Passwords do not match")
            return
        }
        
        // Validate password strength
        if (newPassword.length < 8) {
            showError("Password must be at least 8 characters")
            return
        }
        
        // Call backend API
        resetPasswordApi(token, newPassword)
    }
    
    private fun resetPasswordApi(token: String, newPassword: String) {
        lifecycleScope.launch {
            try {
                val response = apiService.resetPassword(token, newPassword)
                
                // Show success message
                showSuccess("Password reset successful!")
                
                // Navigate to login
                navigateToLogin()
                
            } catch (e: Exception) {
                showError("Failed to reset password: ${e.message}")
            }
        }
    }
}
```

---

## 5. API Service Implementation

```kotlin
interface ApiService {
    
    @POST("auth/forgot-password")
    suspend fun forgotPassword(
        @Body request: ForgotPasswordRequest
    ): Response<ForgotPasswordResponse>
    
    @POST("auth/reset-password")
    suspend fun resetPassword(
        @Body request: ResetPasswordRequest
    ): Response<ResetPasswordResponse>
    
}

data class ForgotPasswordRequest(
    val email: String
)

data class ResetPasswordRequest(
    val token: String,
    val new_password: String
)

data class ForgotPasswordResponse(
    val message: String
)

data class ResetPasswordResponse(
    val message: String
)
```

---

## 6. Testing Deep Linking

### Test via ADB

```bash
# Send deep link to app
adb shell am start -a android.intent.action.VIEW \
  -d "https://kneeoa.online/reset-password?token=YOUR_TOKEN_HERE" \
  com.azfarsuhail.kneeoaapp
```

### Test via Browser

1. Open your app's deep link in a browser:
   ```
   https://kneeoa.online/reset-password?token=YOUR_TOKEN_HERE
   ```

2. Android should prompt: "Open with Knee OA App?"

3. Click **OK** to open the app with the token

### Test with Chrome DevTools

```bash
# Open Chrome with deep link
google-chrome "https://kneeoa.online/reset-password?token=YOUR_TOKEN_HERE"
```

---

## 7. Troubleshooting

### Issue: App doesn't open when clicking link

**Solutions:**
1. Verify `autoVerify="true"` is set in `AndroidManifest.xml`
2. Check SHA-256 fingerprint matches the one in `assetlinks.json`
3. Clear app data and reinstall
4. Verify `assetlinks.json` is accessible: `curl https://kneeoa.online/.well-known/assetlinks.json`

### Issue: Token not extracted from URI

**Solutions:**
1. Check `intent.action == Intent.ACTION_VIEW`
2. Verify `uri.getQueryParameter("token")` is called correctly
3. Add logging to debug URI parsing

### Issue: App Links verification fails

**Solutions:**
1. Verify SHA-256 fingerprint is correct
2. Check package name matches exactly
3. Ensure `assetlinks.json` is served with correct MIME type (`application/json`)
4. Use Android Studio's **Analyze APK** tool to verify

---

## 8. Security Best Practices

### ✅ Implement These Security Measures:

1. **Token Expiry Check**
   - Tokens expire after 15 minutes
   - Show clear error message if expired

2. **One-Time Use**
   - Invalidate token after successful password reset
   - Prevent token reuse

3. **HTTPS Only**
   - All deep links must use HTTPS
   - Android enforces this for App Links

4. **Secure Storage**
   - Don't store tokens in SharedPreferences
   - Use secure in-memory storage

5. **Rate Limiting**
   - Backend should limit reset requests per email
   - Prevent brute force attacks

---

## 9. User Experience Tips

### ✅ Best Practices:

1. **Clear Error Messages**
   - "This reset link has expired. Please request a new one."
   - "Invalid reset link. Please check the URL and try again."

2. **Loading States**
   - Show spinner while validating token
   - Disable submit button during API call

3. **Password Requirements**
   - Display password requirements clearly
   - Show real-time validation feedback

4. **Success Confirmation**
   - Show success message after password reset
   - Auto-navigate to login screen

5. **Resend Link Option**
   - Provide "Resend reset link" button if email not received
   - Add countdown timer before allowing resend

---

## 10. Complete Flow Diagram

```
User clicks "Forgot Password" in app
           ↓
Backend sends email with reset link
           ↓
User clicks link in email
           ↓
Android detects deep link
           ↓
App opens ResetPasswordActivity
           ↓
Token extracted from URI
           ↓
User enters new password
           ↓
Backend validates and updates password
           ↓
Success message shown
           ↓
Navigate to login screen
```

---

## Summary

| Component | Status |
|-----------|--------|
| Android App Links configured | ✅ |
| Deep link handling implemented | ✅ |
| Token extraction from URI | ✅ |
| Password reset API integration | ✅ |
| Security best practices | ✅ |
| User experience optimization | ✅ |

---

**Backend Endpoint:** `https://kneeoa.online/api/v1/auth/reset-password`  
**Deep Link Format:** `https://kneeoa.online/reset-password?token={JWT_TOKEN}`  
**Token Expiry:** 15 minutes  
**Android Package:** `com.azfarsuhail.kneeoaapp`
