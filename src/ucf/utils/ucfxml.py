# coding: utf-8

# GAEGEN2対応:Loggerをカスタマイズ
#import logging
import sateraito_logger as logging
from ucf.utils.ucfutil import UcfUtil

############################################################
### サンプル.START.
############################################################
u'''
			# XML文書作成
			# １．メモリ上で作成する場合
			# XMLドキュメント作成（ノード名を指定. 第二引数は同時に属性をセットする場合の辞書）
			root = UcfXml.createNode('Root', {'attr':'aaa'})

#			# ファイルからXML文書を読み込む
#			root = UcfXml.load('test.xml')

			# ノードを作成
			node1 = UcfXml.createNode('Node1')
			# InnerTextに文字列を設定（サブノードがある場合、そのノードはそのまま残る. text()に値をセットするイメージ）
			node1.setCurrentInnerText('I\'m node1.')
			# InnerTextに文字列を設定（サブノードがある場合、そのノードを削除してからセットする）
#			node1.setInnerText('I\'m node1.')
			# ノードをアペンド
			root.append(node1)

			# InnerText取得
			strvalue = node1.getInnerText()

			# 指定親ノードにサブノードをアペンドしそのノードを返す
			subnode = node1.appendNewNode('SubNode')
			subnode.setCurrentInnerText('I\'m sub node1.')
			subnode = node1.appendNewNode('SubNode')
			subnode.setCurrentInnerText('I\'m sub node2.')

			# １ノード検索
			search_node = root.selectSingleNode('Node1')

			# 複数ノード検索（SelectNodes）
			search_node_list = node1.selectNodes('SubNode')
			
			# ノードリストをループ
			id = 0
			for node in search_node_list:
				id += 1
				# 属性へのアクセス
				# 属性はエレメント保持の辞書オブジェクト風.
				# 存在しなくても下記で作成できる
				# 代入はstr型. int型などはＮＧ.
				node.setAttribute('id', id)
				node.setAttribute('for_del', u'あとで削除する属性')

				# 属性値を取得
				strId = node.getAttribute('id')

			# 属性を削除
			for node in search_node_list:
				node.removeAttribute('for_del')

			# 文字列からノードを作成
			new_node = UcfXml.loadXml('<NewNode>created from string.</NewNode>')
			root.append(new_node)

			# ノードを削除（remove）
			# 準備
			del_node = UcfXml.loadXml('<DelNode attr="abc">for del.<DelSubNode>aaa</DelSubNode></DelNode>')
			root.append(del_node)
			# 削除
			root.remove(del_node)

			# ノード内の子ノードを全て削除する場合（親ノードのtextや属性もオプションによっては削除）
			# 準備
			del_node = UcfXml.loadXml('<DelParentNode attr="abc">for del.<DelSubNode>aaa</DelSubNode></DelParentNode>')
			node1.append(del_node)
			del_parent_node = node1.selectSingleNode('DelParentNode')
			# 削除
			del_parent_node.removeAll()
#			# 削除（属性も削除）
#			del_parent_node.removeAll(attr_delete=True)
#			# 削除（属性だけ全て削除）
#			del_parent_node.removeAllAttributes()

#			# TODO XMLを複製
#
#			# TODO NameSpaceの扱い


			# XMLを文字列として取得
			self.response.out.write(UcfUtil.htmlEncode(root.outerXml()) + "<BR>")
'''
############################################################
### サンプル.END.
############################################################

############################################################
## Xml管理クラス
## XmlParser（ElementTreeなど）のラッパークラス
############################################################
class UcfXml():
	u'''Xml管理クラス'''

	_element = None

	#+++++++++++++++++++++++++++++++++++++++
	#+++ コンストラクタ
	#+++++++++++++++++++++++++++++++++++++++
	def __init__(self, element):
		u'''
		TITLE:コンストラクタ
		PARAMETER:
			element:使用するXmlParserのエレメントオブジェクト
		'''
		if element == None:
			raise Exception('[element] IS NEED.')

		# クラス変数の初期化（コンストラクタで明示的に行わないとインスタンス生成時に初期化されないため）
		self._element = element

	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ [STATIC]ノードを新規作成
	#+++++++++++++++++++++++++++++++++++++++
	def createNode(node_name, attrs=None):
		u'''
		TITLE:[STATIC]ノードを新規作成
		PARAMETER:
			node_name:作成するノード名
			attrs:ノードに属性を同時に追加する場合は指定（属性名と値のハッシュ）
		RETURN:UcfXmlインスタンス
		'''
		from xml.etree import ElementTree

		if attrs != None:
			element = ElementTree.Element(node_name, attrs)
		else:
			element = ElementTree.Element(node_name)
		if element != None:
			node = UcfXml(element)
		else:
			node = None
		return node
	createNode = staticmethod(createNode)
	#+++++++++++++++++++++++++++++++++++++++


	#+++++++++++++++++++++++++++++++++++++++
	#+++ [STATIC]ファイルからXML文書を読み込む
	#+++++++++++++++++++++++++++++++++++++++
	def load(file_path):
		u'''
		TITLE:ファイルからXML文書を読み込む
		PARAMETER:
			xpath:file_path
		RETURN:UcfXmlインスタンス
		'''
		from xml.etree import ElementTree

#			# ２．ファイルからXML文書を読み込む場合（アクセス権限によりXMLファイルを置く場所は限定される。app.yamlの指定次第！？）
#			fd = file('test.xml', 'rb')					# ファイルの存在チェックは事前に必要
#			dom = ElementTree.ElementTree(file=fd)
#			root = dom.getroot()

		# TODO ファイルの事前存在チェック（ファイルがないと↓でエラーするため）

		dom = ElementTree.parse(file_path) 
		root = dom.getroot()
		if root != None:
			node = UcfXml(root)
		else:
			node = None
		return node
	load = staticmethod(load)
	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ [STATIC]文字列からXML文書を読み込む
	#+++++++++++++++++++++++++++++++++++++++
	def loadXml(xml_value):
		u'''
		TITLE:[STATIC]文字列からXML文書を読み込む
		PARAMETER:
			xml_value:xml文字列
		RETURN:UcfXmlインスタンス
		'''
		from xml.etree import ElementTree

		new_node = ElementTree.fromstring(xml_value)
		return UcfXml(new_node)
	loadXml = staticmethod(loadXml)
	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ [STATIC]InnerText文字列を取得
	#+++++++++++++++++++++++++++++++++++++++
	def getInnerTextNvl(node, xpath=''):
		u'''
		TITLE:[STATIC]ノードの指定XPATHのInnerText文字列を取得
		PARAMETER:
			node:対象ノード
			xpath:対象XPATH
		RETURN:文字列（取得できない場合は空文字を【返す）
		'''
		if node == None:
			return ''
		if xpath == None or xpath == '':
			return UcfUtil.nvl(node.getInnerText())

#		hash_node = node.exchangeToHash(isAttr=True, isChild=True)
#		return UcfUtil.nvl(UcfUtil.getHashStr(hash_node, xpath))

		# XPATH 解析（属性とノードに分ける）
		xpath_parts = xpath.split('@')
		xpath_node = xpath_parts[0].rstrip('/')
		xpath_atr = xpath_parts[1] if len(xpath_parts) >= 2 else ''

		node_target = node.selectSingleNode(xpath_node)
		if node_target == None:
			return ''

		if xpath_atr != '':
			return UcfUtil.nvl(node_target.getAttribute(xpath_atr))
		else:
			return UcfUtil.nvl(node_target.getInnerText())
		

	#+++++++++++++++++++++++++++++++++++++++
	#+++ InnerTextに文字列を設定
	#+++++++++++++++++++++++++++++++++++++++
	def setCurrentInnerText(self, text):
		u'''
		TITLE:InnerTextに文字列を設定
		ABSTRACT:サブノードがある場合、そのノードはそのまま残る. text()に値をセットするイメージ
		PARAMETER:
			text:セットする文字列
		'''
		self._element.text = text
	#+++++++++++++++++++++++++++++++++++++++
	
	#+++++++++++++++++++++++++++++++++++++++
	#+++ InnerTextに文字列を設定
	#+++++++++++++++++++++++++++++++++++++++
	def setInnerText(self, text):
		u'''
		TITLE:InnerTextに文字列を設定
		ABSTRACT:サブノードがある場合、そのノードを削除してからセットする
		PARAMETER:
			text:セットする文字列
		'''
		self.removeChildNodes()
		self._element.text = text
	#+++++++++++++++++++++++++++++++++++++++
	
	#+++++++++++++++++++++++++++++++++++++++
	#+++ InnerText文字列を取得
	#+++++++++++++++++++++++++++++++++++++++
	def getInnerText(self):
		u'''
		TITLE:InnerText文字列を取得
		ABSTRACT:直下のTEXTのみを取得.サブノードがあっても無視.
		PARAMETER:
		RETURN:文字列
		'''
		return UcfUtil.nvl(self._element.text)
	
	#+++++++++++++++++++++++++++++++++++++++
	
	#+++++++++++++++++++++++++++++++++++++++
	#+++ 属性に値をセット
	#+++++++++++++++++++++++++++++++++++++++
	def setAttribute(self, name, value):
		u'''
		TITLE:属性に値をセット
		ABSTRACT:属性がなければ作成してセット
		PARAMETER:
			name:属性名
			value:属性値
		'''
		self._element.attrib[name] = UcfUtil.nvl(value)
	#+++++++++++++++++++++++++++++++++++++++
	
	#+++++++++++++++++++++++++++++++++++++++
	#+++ 属性値を取得
	#+++++++++++++++++++++++++++++++++++++++
	def getAttribute(self, name):
		u'''
		TITLE:属性値を取得
		ABSTRACT:属性がなければNoneを返す
		PARAMETER:
			name:属性名
		RETURN:属性値
		'''
		#GAEGEN2対応:Python3文法対応. has_key廃止.辞書型のキー存在チェックは in で行う
		#if self._element.attrib.has_key(name):
		if name in self._element.attrib:
			return self._element.attrib[name]
		else:
			return None

	#+++++++++++++++++++++++++++++++++++++++
	
	#+++++++++++++++++++++++++++++++++++++++
	#+++ 属性を全て取得
	#+++++++++++++++++++++++++++++++++++++++
	def attributes(self):
		u'''
		TITLE:属性を全て取得
		ABSTRACT:ハッシュで全て返す
		PARAMETER:
		RETURN:属性辞書
		'''
		return self._element.attrib

	#+++++++++++++++++++++++++++++++++++++++
	
	#+++++++++++++++++++++++++++++++++++++++
	#+++ 属性を削除
	#+++++++++++++++++++++++++++++++++++++++
	def removeAttribute(self, name):
		u'''
		TITLE:属性を削除
		ABSTRACT:属性がない場合は無視
		PARAMETER:
			name:属性名
		'''
		UcfUtil.removeHash(self._element.attrib, name)

	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ 属性を全て削除
	#+++++++++++++++++++++++++++++++++++++++
	def removeAllAttributes(self):
		u'''
		TITLE:属性を全て削除
		PARAMETER:
		'''
		self._element.attrib.clear()
	#+++++++++++++++++++++++++++++++++++++++
	
	
	#+++++++++++++++++++++++++++++++++++++++
	#+++ 子ノードを追加
	#+++++++++++++++++++++++++++++++++++++++
	def append(self, child):
		u'''
		TITLE:子ノードを追加
		ABSTRACT:
		PARAMETER:
			child:[UcfXml]アペンドする子ノード
		'''
		self._element.append(child._element)
	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ 指定子ノードを削除
	#+++++++++++++++++++++++++++++++++++++++
	def remove(self, child):
		u'''
		TITLE:指定子ノードを削除
		ABSTRACT:
		PARAMETER:
			child:[UcfXml]削除する子ノード
		'''
		self._element.remove(child._element)
	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ 子ノードすべて削除
	#+++++++++++++++++++++++++++++++++++++++
	def removeAll(self, attr_delete=False):
		u'''
		TITLE:子ノードを全て削除
		ABSTRACT:
		PARAMETER:
		'''
		# ループして削除
		for node in [ node for node in self._element]: # ← ループ中のイテレータをそのまま削除はできないため
				self._element.remove(node) # ← ルート.remove ではなく該当親ノードから呼ぶ

		# InnerTextも削除
		self.setCurrentInnerText(None)

		# 属性も削除するなら
		if attr_delete == True:
			self.removeAllAttributes()
	#+++++++++++++++++++++++++++++++++++++++


	#+++++++++++++++++++++++++++++++++++++++
	#+++ 指定親ノードにサブノードをアペンドしそのノードを返す
	#+++++++++++++++++++++++++++++++++++++++
	def appendNewNode(self, node_name):
		u'''
		TITLE:子ノードを追加
		ABSTRACT:
		PARAMETER:
			child:[UcfXml]アペンドする子ノード
		RETURN:追加されたノードのUcfXmlインスタンス
		'''
		from xml.etree import ElementTree
		subnode = ElementTree.SubElement(self._element, node_name)
		if subnode != None:
			node = UcfXml(subnode)
		else:
			node = None
		return node

	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ ノード内の子ノードを全て削除
	#+++++++++++++++++++++++++++++++++++++++
	def removeChildNodes(self):
		u'''
		TITLE:ノード内の子ノードを全て削除
		ABSTRACT:親ノードのtextや属性は削除されない
		PARAMETER:
		'''
		# ループして削除
		for node in [ node for node in self._element]:	# ← ループ中のイテレータをそのまま削除はできないため
				self._element.remove(node)	# ← root.remove ではなく該当親ノードから呼ぶ
	#+++++++++++++++++++++++++++++++++++++++


	#+++++++++++++++++++++++++++++++++++++++
	#+++ XPATHにて１つのノードを検索
	#+++ @はノーサポート
	#+++ 条件式はノーサポート
	#+++++++++++++++++++++++++++++++++++++++
	def selectSingleNode(self, xpath):
		u'''
		TITLE:XPATHにて１つのノードを検索
		PARAMETER:
			xpath:XPATH
		RETURN:UcfXmlインスタンス
		'''
		node = self._element.find(xpath)
		if node != None:
			return UcfXml(node)
		else:
			return None
	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ XPATHにて複数のノードリストを検索
	#+++ @はノーサポート
	#+++ 条件式はノーサポート
	#+++++++++++++++++++++++++++++++++++++++
	def selectNodes(self, xpath):
		u'''
		TITLE:XPATHにて複数のノードリストを検索
		PARAMETER:
			xpath:XPATH
		RETURN:UcfXmlインスタンス一覧
		'''
		search_node_list = self._element.findall(xpath)
		list = []
		if search_node_list != None:
			for node in search_node_list:
				list.append(UcfXml(node))
		return list

	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ 子ノード
	#+++ @はノーサポート
	#+++ 条件式はノーサポート
	#+++++++++++++++++++++++++++++++++++++++
	def exchangeToHash(self, isAttr=False, isChild=False, prefix=''):
		u'''
		TITLE:ノード内の子ノードをハッシュに変換
		ABSTRACT:
		PARAMETER:
		'''
		dic = {}

		# 子ノードをループして追加
		for node in self._element:
			dic_key=prefix + node.tag
			value=node.text
			#GAEGEN2対応:Python3文法対応. has_key廃止.辞書型のキー存在チェックは in で行う
			#if not dic.has_key(dic_key):
			if dic_key not in dic:
				dic[dic_key]=value

				#子ノードも展開
				if isChild:
					#child = UcfXml(node)
					cDic = UcfXml(node).exchangeToHash(isAttr, isChild, prefix=dic_key+'/')
					for k,v in cDic.items():
						#GAEGEN2対応:Python3文法対応. has_key廃止.辞書型のキー存在チェックは in で行う
						#if not dic.has_key(k):
						if k not in dic:
							dic[k]=v

		#属性値をループして追加
		if isAttr:
			for k,v in self.attributes().items():
				k = prefix + '@' + k
				#GAEGEN2対応:Python3文法対応. has_key廃止.辞書型のキー存在チェックは in で行う
				#if not dic.has_key(k):
				if k not in dic:
					dic[k]=v
						
		return dic
	#+++++++++++++++++++++++++++++++++++++++

	#+++++++++++++++++++++++++++++++++++++++
	#+++ OuterXmlを取得
	#+++++++++++++++++++++++++++++++++++++++
	def outerXml(self):
		u'''
		TITLE:OuterXmlを取得
		PARAMETER:
		RETURN:XML文字列
		'''
		from xml.etree import ElementTree
		return ElementTree.tostring(self._element,'utf-8')
	#+++++++++++++++++++++++++++++++++++++++

