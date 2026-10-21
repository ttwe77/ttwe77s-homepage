---
title: 骗过3个Ai的代码
description: 通过一段混用 Python 与 C/Java 风格的代码，展示 Python 中分号、大括号被解析为集合等冷门语法，并记录三个 AI 的识别与实测过程。
date: 2026-10-20
category: 编程
readtime: 6
author: ttwe77
tags: Python, AI, 整活, 语法,, 编程
license: CC BY-NC 4.0
license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
updated: 2026-10-21
---

# 骗过3个Ai的代码

## 开头

最近我开始学习 <span class="hover-hint">Python<span class="hover-hint__tooltip"><span class="hint-title">Python（编程语言）</span>一种解释型、动态类型的高级编程语言。它用缩进表示代码块，语法相对简洁。</span></span> 然后发现有点“水土不服”

> *你这个Python<span class="hover-hint">大括号<span class="hover-hint__tooltip"><span class="hint-title">大括号</span>在 C/Java 中常表示代码块；在 Python 中通常表示字典或集合，不表示代码块。本文正是利用了这个特点。</span></span>呢？句末不用写<span class="hover-hint">分号<span class="hover-hint__tooltip"><span class="hint-title">分号</span>在 Python 中可以作为“语句分隔符”，让一行写多条简单语句；它不是句末必须写的符号。放在 # 后面则会被当成注释内容。</span></span>的吗？？*

后来了解到Python用的<span class="hover-hint">缩进<span class="hover-hint__tooltip"><span class="hint-title">缩进</span>行首的空格或制表符。Python 用缩进来表示代码块的层级；缩进错了可能导致报错或逻辑改变。</span></span>来代替大括号。之前Java、C++写得多了有点不习惯。

> *emmmm我就想如果我硬要上大括号和分号呢？*

于是我写了第一版代码来适应一下：

```python
#斐波那契数列
a=1;
b=1;
print(a);
print(a);

while a<150:#{
    #1+1=2,3+5=8 b=5,a=2
    c=a+b;
    print(c);

    #1+2=3,5+8=13 c=8
    a=b;
    b=a+c;
    print(b);

    #2+3=5
    a=b;
    b=c+b;
    print(b);
#}
```

第一次写的，很乱。我用“#”把大括号<span class="hover-hint">注释<span class="hover-hint__tooltip"><span class="hint-title">注释</span>从 # 到本行末尾的内容会被 Python 忽略，用来写说明，或临时“注释掉”一段代码。</span></span>掉，这样才有点适应。

然后我开始思考能不能把“#”去掉，于是我去B站上找到了一个很新奇的写法：

```python
a = 5;
if (a>3):{
    print(">3")
}
elif (a==3):{
    print("=3")
}
else:{
    print("<3")
}
```

啊把条件用小括号括起来，然后就能用大括号了。嘿嘿嘿这样写还挺好玩的。

既然都写成这样了，那就贯彻到底咯~

```python
int; a = 5;
if (a>3):{
    print(">3")#;
}
elif (a==3):{
    print("=3")#;
}
else:{
    print("<3")#;
}
```

OK啊现在我这个代码是3不像：既不像Python、又不像Java、又不像C++。

我本来想在print()后面添加分号的，但是这样做就会报错。

> *<span class="hover-hint">代码一定要能跑<span class="hover-hint__tooltip"><span class="hint-title">XX一定要XX（梗）</span>“XX一定要XX”这个梗，本质上是网络“**将军梗**”的核心句式，主要用来**调侃或讽刺将理所当然的常识，包装成“重要指示”来说的“废话文学”**。<br>它起源于中文互联网对朝鲜相关宣传视频的二次创作和解构。在这些视频里，“将军”经常在视察各行各业时作出“指导”，似乎对任何事情都了如指掌。网友们于是抓住这种“**什么都懂、什么都要指导**”的观感，创造了这个句式来调侃：仿佛“将军”对着任何事物，都能发表一番看似重要、实则无比正确的“指示”。<br>这个梗的用法非常简单，精髓在于**用极其严肃的语气，说一句绝对正确但毫无信息量的废话**。</span></span>*

好那就这样了。然后我把这些统统发给Ai让他们辨别一下这是什么语言。

### 实测记录

#### DeepSeek

先来看看蓝色大肥鱼能不能辨认出来，结果它说我给的代码**不属于任何主流的标准编程语言**，更像是为了教学目的的**<span class="hover-hint">伪代码<span class="hover-hint__tooltip"><span class="hint-title">伪代码</span>用类似编程语言的方式描述逻辑，但不保证能真正运行。文中 AI 最初误以为这段代码是伪代码。</span></span>**。

然后我就截了个运行成功的图并挑衅地问它：**那你给我解释一下为什么可以运行**

DeepSeek在思考14秒后直接滑跪，说：

> “非常抱歉，我之前的判断确实不够严谨。看到这张运行成功的截图……**我必须承认：这是一段完全合法的 Python 代码（利用了 Python <span class="hover-hint">语法<span class="hover-hint__tooltip"><span class="hint-title">语法规则</span>一种编程语言允许的写法和结构。不符合规则时，解释器会报错。</span></span>的冷门特性/漏洞）**。”
> “它之所以能运行，是因为 Python <span class="hover-hint">解释器<span class="hover-hint__tooltip"><span class="hint-title">解释器</span>负责读取并执行 Python 代码的程序。文中说“用 Python 跑一下”，就是让解释器执行代码。</span></span>并没有把 `{}` 当作像 C/Java 那样的<span class="hover-hint">代码块<span class="hover-hint__tooltip"><span class="hint-title">代码块</span>逻辑上归为一组、一起执行的语句。C、Java 常用 {} 表示代码块，Python 用缩进表示。</span></span>，而是把它当成了“<span class="hover-hint">集合<span class="hover-hint__tooltip"><span class="hint-title">集合(Set)</span>一种无序、元素不重复的容器，通常写成 {1, 2, 3}。空集合要写 set()，因为 {} 表示空字典。</span></span> (Set)”或“<span class="hover-hint">字典<span class="hover-hint__tooltip"><span class="hint-title">字典（dict）</span>一种“键值对”容器，写成 {"name": "Tom", "age": 18}。空字典写作 {}。</span></span> (Dict)”<span class="hover-hint">字面量<span class="hover-hint__tooltip"><span class="hint-title">字面量</span>直接写在代码里的值，例如数字 5、字符串 ">3"、集合 {1, 2}、字典 {"a": 1}。</span></span>。”

#### 豆包

好的来看看下一位选手——<span class="hover-hint">逗包<span class="hover-hint__tooltip"><span class="hint-title">豆包（梗）</span>态度满分、能力随缘、道歉超快、下次还敢</span></span>。（豆包 2.1 Lite 中等级的思考强度）

我还是一样把代码发给豆包问它这是什么语言。它说这**不是任何一种真实存在的编程语言**，而是一段把 Python 和 C/Java 语法硬拼在一起的<span class="hover-hint">“缝合怪”代码<span class="hover-hint__tooltip"><span class="hint-title">“缝合怪”代码</span>非正式说法，指混用多种编程语言风格的代码。本文代码就是 Python 中混入 C/Java 风格符号的例子。</span></span>。

因为我开的是豆包工作模式嘛，这个模式可以执行命令，于是我说：**你用 python 跑一下看看有没有报错**

豆包果然调用了云端环境去跑了我的代码，过了一会豆包的<span class="hover-hint">思维链<span class="hover-hint__tooltip"><span class="hint-title">AI思维链</span>AI 展示或记录的推理过程。文中指 AI 在尝试判断、运行、验证代码时的思考记录。</span></span>：

> 居然**跑通了，没有报错**，输出 `>3`，<span class="hover-hint">退出码<span class="hover-hint__tooltip"><span class="hint-title">退出码</span>程序结束后返回给系统的一个状态码。通常 0 表示成功，非 0 表示出现某种错误。</span></span> 0。
>
> 我刚才判断它会报 <span class="hover-hint">SyntaxError<span class="hover-hint__tooltip"><span class="hint-title">SyntaxError</span>Python 无法理解代码结构时抛出的错误，例如括号不配对、关键字位置不对等。</span></span> 是错的 ——Python 真的接受了这段代码。让我验证一下它到底是怎么被解析的，再测一下 `elif` 和 `else` 分支是不是也能正常走。

> ```shell
> cd /home/user/Doubao/chats/38448306594517762 && echo "=== 测试1: a=3 走 elif ===" && python3 -c "
> a = 3
> if (a>3):{
>     print('>3')#;
> }
> elif (a==3):{
>     print('=3')#;
> }
> else:{
>     print('<3')#;
> }
> "
> echo "=== 测试2: a=2 走 else ===" && python3 -c "
> a = 2
> if (a>3):{
>     print('>3')#;
> }
> elif (a==3):{
>     print('=3')#;
> }
> else:{
>     print('<3')#;
> }
> "
> echo "=== 测试3: 确认大括号被当成 set 字面量 ===" && python3 -c "
> x = {print('hi')}
> print(type(x), x)
> "
> 
> === 测试1: a=3 走 elif ===
> =3
> === 测试2: a=2 走 else ===
> <3
> === 测试3: 确认大括号被当成 set 字面量 ===
> hi
> <class 'set'> {None}
> ```

> 实测结果：**完全能跑，三个分支都正常工作。**

哈哈哈看来理论再多，都不如让代码跑起来得实在。豆包这波光速打脸。

#### 某西方AI

这个AI的名字在这里不方便说，我描述一下：

> *免费版有知识截止，Plus能切模型、用插件、画图、读文件，后来还加了记忆和画布的那个对话产品。logo长得像**鹦鹉螺壳**（我的世界）*

好来看看西方Ai的实力。我依旧复制粘贴然后发送。它说：

> 这段代码看起来像是 **C 语言和 Python 的混血产物**，但目前看不出它属于任何一种主流编程语言。它大概想同时享受两种语言的优点，**最后把两种语言的语法规则给惹毛了。**

我啊，微微一笑。给它发了相同的话：“**你用python跑一下看看有没有报错**”。

不到一分钟，它也败下阵来，说：

> 我用 Python 实际运行了你给的代码，结果有点出乎意料：**没有报错，正常输出了 `>3`**。
>
> ```TEXT
> >3
> ```
>
> 更离谱的是，它居然真的符合 Python 的语法规则。

## 解释

众所周知把知识教给别人学习最快，所以我尝试和蓝色大肥鱼一起跟你们解释一下。

先看代码：

```python
int; a = 5;
if (a>3):{
    print(">3")#;
}
elif (a==3):{
    print("=3")#;
}
else:{
    print("<3")#;
}
```

## 第一行 int

首先来看第一行，这个`int; a = 5;`中的分号表示的是**分割符**，就相当于：

```python
int
a = 5
```

> [!note]
>
> **Python 看到 `int` 会去“查这个名字是谁”**、**查完算出一个结果**、**但脚本不会自动把结果打印出来**。

单独执行 `int` 是这样的：

```python
>>> int
<class 'int'>
```

简单的说就是Python在执行这个指令的时候，直接把返回的内容扔掉了（不是`print`或<span class="hover-hint">赋值<span class="hover-hint__tooltip"><span class="hint-title">赋值</span>把某个值绑定给变量，例如 a = 5 表示让变量 a 指向整数 5。</span></span>）。

然后就是

## 第二行 if

灵感来源： [python迷惑行为：我有了花括号 { }](https://www.bilibili.com/video/BV1a84y1t7c5/)

来看第二行：

```python
if (a>3):{
```

这里的小括号就只是把 `a>3` 包起来而已，没有特殊含义。

而这里的大括号：

```python
if (a>3):{
    print(">3")#;
}
```

是将代码当成了集合，就像：

```python
{ print(">3") }
```

也可以加入更多内容：

```python
{ b<span class="hover-hint">:=<span class="hover-hint__tooltip"><span class="hint-title">海象运算符 :=</span>Python 3.8 引入的“赋值表达式”，可以在表达式内部给变量赋值并返回该值，例如 b := 5。</span></span>5 , print(">3") , print(b) }
```

执行返回：

```python
>>> { b:=5 , print(">3") , print(b) }
>3
5
{None, 5}
```

> [!note]
>
> 后者a=10要写成a:=10
>
> 赋值<span class="hover-hint">语句<span class="hover-hint__tooltip"><span class="hint-title">语句</span>执行某个动作的代码单位，例如赋值语句 a = 5、条件语句 if ...、函数调用 print(...)。</span></span>本身不能在集合内
>
> ​       ---[伊桑桑桑桑桑](https://space.bilibili.com/397069113)

## 第三行 #;

```python
    print(">3")#;
```

这里没啥好讲的。`#` 后面的内容是注释，会被Python忽略。

如前面的例子，也可以这么用：

```python
if a==1:#{
    print("a=1")
#}
```

## 结语

哈哈哈这3个AI好逗，我这“三不像”代码成功地把AI迷住了。

主要是喜欢看AI“滑跪”。看它们一本正经地说非主流，而正在跑起来又没有报错。

这种**反差感**，比代码本身还好玩。

代码不一定要永远正经。偶尔把它当玩具，试试“如果硬要这样写会怎样”，然后看解释器和 AI 一起露出问号脸，本身就是学习里很有意思的一部分。**失败了是实验，跑通了是节目效果。**



**代码一定要能跑，快乐一定要分享。**
