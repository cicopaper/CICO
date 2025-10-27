PY_EXAMPLE = (
"""
def parse_repo_to_func(self, repo_path: str):
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(self.lan_suffix):
                file_path = os.path.join(root, file)
                root_node = self.parse_ast(file_path)
                fun_list = self.extract_func_list(root_node)
                self.function_data.extend(fun_list)           
    
    fun_comment_list = []
    comment_code_list = []
    for f in self.function_data: 
        comment_list = self.parse_fun_to_comment(f['func_node'])
        if f['doc'] != '':
            fun_comment_list.append({
                "doc": f['doc'],
                "signature": self.get_function_signature(f['func_node']),
                "comments": self.nodestostr([c[0] for c in comment_list])
            })
            comment_code_list.append([fun_comment_list[-1]['doc'], self.nodetostr(f['func_node'])])
        comment_code_list.extend(comment_list)

    comment_code_dict = {}
    for cc in comment_code_list:
        if cc[0] in comment_code_dict:
            comment_code_dict[cc[0]] += cc[1]
        else:
            comment_code_dict[cc[0]] = cc[1]
    return fun_comment_list, comment_code_dict
""",
"""
def parse_repo_to_func(self, repo_path: str):
    \"\"\"
    parse the repository to extract function and comment data, return the function comment to function code dict and comment to code dict
    Args:
        repo_path (str): the path of the repository
    \"\"\"

    # walk through the repo and parse functions with ast
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(self.lan_suffix):
                file_path = os.path.join(root, file)
                root_node = self.parse_ast(file_path)
                fun_list = self.extract_func_list(root_node)
                self.function_data.extend(fun_list)           
    
    # extract the function to comment data and comment to code data
    fun_comment_list = []
    comment_code_list = []
    for f in self.function_data:
        comment_list = self.parse_fun_to_comment(f['func_node'])
        if f['doc'] != '':
            fun_comment_list.append({
                "doc": f['doc'],
                "signature": self.get_function_signature(f['func_node']),
                "comments": self.nodestostr([c[0] for c in comment_list])
            })
            comment_code_list.append([fun_comment_list[-1]['doc'], self.nodetostr(f['func_node'])])
        comment_code_list.extend(comment_list)

    # transfer the comment to code data into a dict and add the same key code together
    comment_code_dict = {}
    for cc in comment_code_list:
        if cc[0] in comment_code_dict:
            comment_code_dict[cc[0]] += cc[1]
        else:
            comment_code_dict[cc[0]] = cc[1]
    return fun_comment_list, comment_code_dict
"""
)

JAVA_EXAMPLE = (
"""
public byte[] sign(InputStream content) throws IOException {
    try {
        CMSSignedDataGenerator gen = new CMSSignedDataGenerator();
        X509Certificate cert = (X509Certificate) certificateChain[0];
        ContentSigner sha1Signer = new JcaContentSignerBuilder("SHA256WithRSA").build(privateKey);
        gen.addSignerInfoGenerator(new JcaSignerInfoGeneratorBuilder(new JcaDigestCalculatorProviderBuilder().build()).build(sha1Signer, cert));
        gen.addCertificates(new JcaCertStore(Arrays.asList(certificateChain)));
        
        CMSProcessableInputStream msg = new CMSProcessableInputStream(content);
        CMSSignedData signedData = gen.generate(msg, false);
        if (tsaUrl != null && !tsaUrl.isEmpty()) {
            ValidationTimeStamp validation = new ValidationTimeStamp(tsaUrl);
            signedData = validation.addSignedTimeStamp(signedData);
        }
        
        return signedData.getEncoded();
    } catch (GeneralSecurityException | CMSException | OperatorCreationException | URISyntaxException e) {
        throw new IOException(e);
    }
}
""",
"""
/**
 * Sign the content of an input stream with a digital signature
 * This method creates a CMS digital signature for the given input stream content using a private key.
 * @param content The input stream data to be signed
 * @return Byte array containing the encoded signed data
 * @throws IOException When an IO exception or other security exception occurs during signing
 */
public byte[] sign(InputStream content) throws IOException {
    try {
        // Initialize the CMS signed data generator and configure it with the signer's certificate and private key
        CMSSignedDataGenerator gen = new CMSSignedDataGenerator();
        X509Certificate cert = (X509Certificate) certificateChain[0];
        ContentSigner sha1Signer = new JcaContentSignerBuilder("SHA256WithRSA").build(privateKey);
        gen.addSignerInfoGenerator(new JcaSignerInfoGeneratorBuilder(new JcaDigestCalculatorProviderBuilder().build()).build(sha1Signer, cert));
        gen.addCertificates(new JcaCertStore(Arrays.asList(certificateChain)));
        
        // Generate the CMS signed data from the input stream and optionally add a timestamp if a TSA URL is provided
        CMSProcessableInputStream msg = new CMSProcessableInputStream(content);
        CMSSignedData signedData = gen.generate(msg, false);
        if (tsaUrl != null && !tsaUrl.isEmpty()) {
            ValidationTimeStamp validation = new ValidationTimeStamp(tsaUrl);
            signedData = validation.addSignedTimeStamp(signedData);
        }

        return signedData.getEncoded();
    } catch (GeneralSecurityException | CMSException | OperatorCreationException | URISyntaxException e) {
        throw new IOException(e);
    }
}
"""
)
GO_EXAMPLE = (
"""
func getAssetUSDPrice(body, currency string) (float64, error) {
    if currency == "USD" {
        return 1.0, nil
    } else if currency == "" {
        return 0.0, nil
    }

    m := make(map[string]interface{})
    json.Unmarshal([]byte(body), &m)
    rates := make(map[string]interface{})

    var ok bool
    if rates, ok = m["rates"].(map[string]interface{}); !ok {
        return 0.0, fmt.Errorf("could not get rates from api response")
    }

    var rate float64
    if rate, ok = rates[currency].(float64); !ok {
        return 0.0, fmt.Errorf("could not get rate for %s", currency)
    }

    return rate, nil
}
""",
"""
/**
 * Gets the USD price of an asset by extracting exchange rate information from a JSON response body and converting the specified currency to USD value.
 */
func getAssetUSDPrice(body, currency string) (float64, error) {
    // For USD currency, return the exchange rate of 1.0 since one USD equals one USD with no conversion needed
    if currency == "USD" {
        return 1.0, nil
    } else if currency == "" {
        return 0.0, nil
    }

    // Parse the JSON response body into a map 
    m := make(map[string]interface{})
    json.Unmarshal([]byte(body), &m)
    rates := make(map[string]interface{})

    // If rates cannot be found or is not in the expected format, return error
    var ok bool
    if rates, ok = m["rates"].(map[string]interface{}); !ok {
        return 0.0, fmt.Errorf("could not get rates from api response")
    }

    // Get the specific exchange rate for the requested currency, error if not found
    var rate float64
    if rate, ok = rates[currency].(float64); !ok {
        return 0.0, fmt.Errorf("could not get rate for %s", currency)
    }

    return rate, nil
}
"""
)