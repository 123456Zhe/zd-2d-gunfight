# Jujutsu (jj) 与 Git 兼容使用指南

## 配置说明

已配置 `~/.jjconfig.toml` 使 jj 与 Git 无缝协作。

## 常用命令对照

### 查看状态
```bash
# Git
git status

# Jujutsu
jj status
```

### 查看日志
```bash
# Git
git log --oneline

# Jujutsu
jj log
```

### 提交更改
```bash
# Git
git add .
git commit -m "提交信息"

# Jujutsu
jj commit -m "提交信息"
```

### 创建分支/Bookmark
```bash
# Git
git checkout -b feature-branch

# Jujutsu
jj bookmark create feature-branch
```

### 切换分支
```bash
# Git
git checkout branch-name

# Jujutsu
jj edit bookmark-name
# 或
jj edit revision-id
```

### 推送到远程
```bash
# Git
git push origin branch-name

# Jujutsu
jj git push --bookmark bookmark-name
```

### 拉取更新
```bash
# Git
git pull

# Jujutsu
jj git fetch
jj rebase -d @- --onto origin/main
```

## 高级特性

### 1. 自动同步 Git 分支
配置已启用 `templates.git_push_bookmark`，推送时会自动生成 Git 分支名。

### 2. 撤销更改
```bash
# 撤销工作区更改
jj restore

# 撤销到指定版本
jj edit revision-id
```

### 3. 查看差异
```bash
jj diff
```

### 4. 变基操作
```bash
jj rebase -d target-revision
```

## 注意事项

1. **Git HEAD**: jj 会自动跟踪 Git 的 HEAD 位置
2. **分支映射**: jj 的 bookmark 会自动映射到 Git 的 branch
3. **协作**: 可以与使用 Git 的团队成员无缝协作

## 当前仓库状态

- Git 远程: `origin https://github.com/123456Zhe/zd-2d-gunfight.git`
- 当前提交: `cacbd2b0` (更新 .gitignore，忽略 nul 文件)
- 分支: `test`
