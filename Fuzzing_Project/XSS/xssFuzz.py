from urllib.parse import urljoin, urlparse, urlencode, parse_qs
from bs4 import BeautifulSoup
from Logging import log as Log
from Logging import progressBar
from WebConfig import web

# sinh payload dưới dạng list từ file xss.txt có sẵn các payload
f = open("XSS/xss.txt", "r")
payloads = []
for pay in f.readlines():
    payloads.append(pay.strip())

"""
scan_form_in_url(url, vulnerable_url) :
 hàm này dùng để scan các lỗi xss thông qua thẻ <form> trong html cái này là cái chính đọc cho kỹ
 ví dụ nhá : 
 <form action="search.php?test=query" method="post"> 
      <label>search art</label> 
      <input name="searchFor" type="text" size="10"> 
      <input name="goButton" type="submit" value="go"> 
</form>

    thì để request trong python với một form như này module requests sẽ yêu cầu chuyền vào 
    tham số data={} (dạng dictionary)

    ví dụ như trong form trên thì requests yêu cầu data/param sẽ là {"searchFor":"duc dep trai","goButton":"goButton"}
    với logic như thế mình sẽ chèn payload vào form với dạng như sau {"searchFor":"<script>prompt(document.cookie)</script>","goButton":"goButton"}

    với hàm này ta sử dụng hàm BeautifulSoup để phân tích html nó sẽ phân tích html ra các thẻ và để tìm kiếm các thẻ ta 
    sử dụng hàm find_all
    ví dụ nhá :
    soup = BeautifulSoup(html.text, 'html.parser')
    forms = soup.find_all('form', method=True)
    còn cái bên dưới này là để lấy các giá trị trả về từ module requests
    html = web.getHTML(url) 
    
    - logic để tìm kiếm lỗi này là sau khi gửi đi request thì reponse trả về là một dạng html bây giờ ta sẽ phân tich 
    cái html đó nếu trong cái html mà có <script>prompt(document.cookie)</script> thì nó là có lỗi xss
"""


def scan_form_in_url(url, vulnerable_url, cookies=None):
    #hàm getHTML gủi yêu cầu HTTP đến URL được cung cấp và trả về đối tượng response được lưu trong biến html
    html = web.getHTML(url, cookies=cookies)
    # nếu việc gửi yêu cầu lên web thành công
    if html:
        # sử dụng thư viện beautifulsoup để phân tích cú pháp HTML và tìm tất cả các thẻ <form> trong HTML
        soup = BeautifulSoup(html.text, 'html.parser')
        forms = soup.find_all('form', method=True)
        # Với mỗi thẻ form tìm được
        for form in forms:
            """
            kiểm tra action hay còn gọi là phần query của một url,nếu tồn tại thuộc tình này thì sử dụng giá trị của 
            nó làm URL,còn không thì sử dụng URL ban đầu được cung cấp
            """
            try:
                action = form['action']
            except KeyError:
                action = url
            """
            đồng thời kiểm tra xem phương thức gửi yêu cầu được sử dụng trong form là get hay post, nếu không
            tồn tại method nào thì để mặc định là get, tác dụng của việc này sẽ được nói ở phần dưới
            """
            try:
                # print('method : ' + form['method'])
                method = form['method'].lower().strip()
            except KeyError:
                method = 'get'
            """
             sử dũng kỹ thuật tấn công brute force đẩy gửi liên tục các dữ liệu payload lên máy chủ web 
             để lấy mã html trả về và lặp qua từng phần tử của form (thẻ input và textarea) để tạo dữ liệu fuzzing
             (thông thường dữ liệu để post có dạng là dictionary trong python)
            """
            i = 0
            for payload in payloads:
                keys = {}
                for key in form.find_all(["input", "textarea"]):
                    try:

                        if key['type'] == 'submit':
                            try:
                                keys.update({key['name']: key['name']})
                            except Exception as e:
                                keys.update({key['value']: key['value']})
                        else:
                            keys.update({key['name']: payload})
                    except Exception as e:
                        Log.warning('Internal error: ' + str(e))
                        if method.lower().strip() == 'get':
                            try:
                                keys.update({key['name']: payload})
                            except KeyError as e:
                                    Log.warning('Internal error: ' + str(e))
                # {'name' : '<script>alert(document.cookie)</script>',}
                # bat dau set requests (manh duc)
                final_url = urljoin(url, action)
                if method.lower().strip() == 'get':
                    req_html = web.getHTML(final_url, method=method.lower(), params=keys, cookies=cookies)
                    if payload in req_html.text:
                        Log.high(Log.R + ' Vulnerable deteced in url/form :' + final_url)
                        vulnerable_url.append([final_url, 'form', 'xss', payload])
                        break
                elif method.lower().strip() == 'post':
                    req_html = web.getHTML(final_url, method=method.lower(), data=keys, cookies=cookies)
                    if payload in req_html.text:
                        Log.high(Log.R + ' Vulnerable deteced in url/form :' + final_url)
                        vulnerable_url.append([final_url, 'form', 'xss', payload])
                        break


"""
scan_in_a_url(url, vulnerable_url):
    như này nhá :
    - thì một url như này https://manhducyeudeptrai.com//?id=1 thì sẽ có các thành phần 
    id=1 thành phần này gọi là query dùng để đưa dữ liệu cần tìm kiếm vào để tìm kiếm như ở đây nó sẽ tìm những thằng có id bằng 1
    theo cách này ta tìm cách  đẩy các dữ liệu không hợp lê (payload) vào cái thành phần query này 
    - để có thể tách được thành phần query này ra khỏi url thì mình dùng urlparse từ module urllib.parse
    ví dụ : queries = urlparse(url).query -> nó sẽ tách thành phần url thành id=1
    - ờm dcm thì sau khi tách được id=1 thì mình chèn payload vào nhá như này id=<script>prompt(document.cookie)</script>
    - rồi để có thể kiểm tra được thì ta sẽ phải nối thành phần url với thành phần query như này :
    https://manhducyeudeptrai.com/ +  id=<script>prompt(document.cookie)</script> -> https://manhducyeudeptrai.com/?id=<script>prompt(document.cookie)</script>
    - rồi sau đó mình request cái url để lấy html trả về nếu có <script>prompt(document.cookie)</script> thì nó có thể có lỗi xss
"""


def scan_in_a_url(url, vulnerable_url, cookies=None):
    query = urlparse(url).query
    if query != '':
        for payload in payloads:
            query_payload = query.replace(query[query.find('=') + 1:len(query)], payload, 1)
            check_url = url.replace(query, query_payload, 1)
            Log.info('parse query' + str(parse_qs(query)))
            check_url_query_all = url.replace(query, urlencode({x: payload for x in parse_qs(query)}))
            Log.info('check_url_query_all : ' + str(check_url_query_all))
            # {'name' : }
            req_1 = web.getHTML(check_url, verify=False)
            req_2 = web.getHTML(check_url_query_all)

            if req_2:
                if payload in req_1.text or payload in req_2.text:
                    Log.high(Log.R + ' Vulnerable deteced in url :' + check_url_query_all)
                    vulnerable_url.append([check_url, 'url/href', 'xss', payload])
                    return True
        return False
    return False




"""cái này dùng để test thui"""


def scan_xss(url, method=2, cookies=None):
    vulnerable_url = []
    if method >= 2:
        scan_in_a_url(url, vulnerable_url)
        scan_form_in_url(url, vulnerable_url)
        if len(vulnerable_url):
            return True, vulnerable_url
        else:
            return False
    elif method == 1:
        scan_in_a_url(url, vulnerable_url)
        scan_form_in_url(url, vulnerable_url)
        if len(vulnerable_url):
            return True, vulnerable_url
        else:
            return False
    elif method == 0:
        scan_form_in_url(url, vulnerable_url)
        if len(vulnerable_url):
            return True, vulnerable_url
        else:
            return False
