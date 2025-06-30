# 🚀 Vercel Deployment Settings for Meesho Order Scanner

## ⚙️ **Vercel Dashboard Settings:**

### **1. Framework Preset:**
```
Framework Preset: Other
```
**✅ DO NOT select Flask/Python** - Use "Other" for custom configuration

### **2. Root Directory:**
```
Root Directory: ./
```
**✅ Leave empty or use "./"** - Your files are in the root

### **3. Build Settings:**

#### **Build Command:**
```
Build Command: [Leave Empty]
```
**✅ No build command needed** - Python handles this automatically

#### **Output Directory:**
```
Output Directory: [Leave Empty]
```
**✅ No output directory needed** - Flask serves directly

#### **Install Command:**
```
Install Command: pip install -r requirements.txt
```
**✅ Vercel auto-detects this** - Can leave empty

### **4. Environment Variables:**

Add these in Vercel Dashboard → Settings → Environment Variables:

| **Key** | **Value** | **Environment** |
|---------|-----------|-----------------|
| `FLASK_ENV` | `production` | Production |
| `UPLOAD_FOLDER` | `/tmp` | All |

### **5. Functions Configuration:**
```json
{
  "functions": {
    "app.py": {
      "maxDuration": 30
    }
  }
}
```

## 📋 **Complete Vercel Deployment Checklist:**

### **Step 1: Prepare Your Repository**
- ✅ `vercel.json` file (already created)
- ✅ `requirements.txt` with all dependencies
- ✅ `app.py` as main application file
- ✅ `templates/` folder with HTML files
- ✅ `.gitignore` file

### **Step 2: Vercel Dashboard Settings**
1. **Import Project**: Connect your GitHub repo
2. **Framework Preset**: Select "Other"
3. **Root Directory**: Leave empty or "./"
4. **Build Command**: Leave empty
5. **Output Directory**: Leave empty
6. **Environment Variables**: Add the ones listed above

### **Step 3: Deploy**
- Click "Deploy"
- Wait 2-3 minutes
- Your app will be live! 🎉

## 🔧 **Advanced Configuration (Optional):**

If you want more control, update your `vercel.json`:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "50mb"
      }
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/app.py"
    }
  ],
  "env": {
    "FLASK_ENV": "production",
    "UPLOAD_FOLDER": "/tmp"
  },
  "functions": {
    "app.py": {
      "maxDuration": 30
    }
  }
}
```

## ⚡ **Quick Deploy Commands:**

```bash
# 1. Initialize git (if not done)
git init
git add .
git commit -m "Deploy to Vercel"

# 2. Push to GitHub
git remote add origin https://github.com/yourusername/meesho-scanner.git
git push -u origin main

# 3. Or use Vercel CLI
npx vercel --prod
```

## 🎯 **Expected Result:**

- ✅ **Live URL**: `https://your-project-name.vercel.app`
- ✅ **HTTPS enabled**: Camera access works
- ✅ **Global CDN**: Fast loading worldwide
- ✅ **Auto SSL**: Secure by default
- ✅ **All features working**: PDF upload, scanning, export

## 🚨 **Common Issues & Solutions:**

### **Issue 1: Build Fails**
**Solution**: Make sure `requirements.txt` is in root directory

### **Issue 2: Camera Not Working**
**Solution**: Vercel automatically provides HTTPS - should work

### **Issue 3: File Upload Issues**
**Solution**: Files go to `/tmp` in serverless - this is normal

### **Issue 4: App Not Loading**
**Solution**: Check `app.py` is in root and has `if __name__ == '__main__':`

## 🎉 **That's It!**

With these settings, your Meesho Order Scanner will deploy perfectly to Vercel with full functionality maintained!
