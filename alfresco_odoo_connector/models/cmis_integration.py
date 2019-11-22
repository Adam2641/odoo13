import cmislib
import logging
import ntpath
import  os

root_path = os.path.dirname(os.path.abspath(__file__))
class CMISController(object):

    def __init__(self, domain_url, user_name, pass_word):

        self._logger = logging.getLogger('CMIS Wrapper')
        self._cmis_conn = cmislib.CmisClient(domain_url,user_name,pass_word)

    def get_root_directory(self):
        """
        get alfresco root directory
        :return:
        """

        try:
            repo = self._cmis_conn.defaultRepository
            root_folder = repo.rootFolder
            return root_folder
        except Exception as err:
            self._logger.error(err)
            return False

    def get_folder_instance(self, root_folder, directory_name):

        try:
            children = root_folder.getChildren()
            directory_instance = None
            for child in children:
                folder_name = child.name
                if folder_name == directory_name:
                    directory_instance = child
                    break
            return directory_instance
        except Exception as err:
            self._logger.error(err)
            return False

    def remove_file_instance(self, directory_name,file_name):

        try:
            root_folder = self.get_root_directory()
            if not root_folder == False:
                self._logger.error("Some Error occured while getting root node")
                return False
            else:
                folder_instance = self.get_folder_instance(root_folder, directory_name)
                if folder_instance == False:
                    self._logger.error("Some Error occured while getting specified folder node")
                    return False
                else:
                    if folder_instance == None:
                        self._logger.debug(directory_name + " Folder not found skipping ..")
                    else:
                        file_already_exist_object = self.check_duplicate_file(folder_instance, file_name)
                        if file_already_exist_object:
                            self.delete_file(file_already_exist_object)
                        else:
                            self._logger.debug("File does not exist skipping.....")
            return True
        except Exception as err:
            self._logger.error(err)
            return False

    def create_directory(self,folder_name):

        try:
            root_folder = self.get_root_directory()
            if root_folder==False:
                self._logger.error("Some Error occured while getting root node")
                return False
            else:
                folder_instance = self.get_folder_instance(root_folder,folder_name)
                if folder_instance==False:
                    self._logger.error("Some Error occured while getting specified folder node")
                    return False
                else:
                    if folder_instance==None:
                        self._logger.debug(folder_name + " Folder not found adding new folder")
                        root_folder.createFolder(folder_name)
                    else:
                        self._logger.debug(folder_name + " already exist so skipping.....")
            return folder_name
        except Exception as err:
            self._logger.error(err)
            return False

    def create_subdirectory(self,main_folder,folder_name):

        try:
            root = self.get_root_directory()
            root_folder = self.get_folder_instance(root,main_folder)
            if root_folder==False:
                self._logger.error("Some Error occured while getting root node")
                return False
            else:
                folder_instance = self.get_folder_instance(root_folder,folder_name)
                if folder_instance==False:
                    self._logger.error("Some Error occured while getting specified folder node")
                    return False
                else:
                    if folder_instance==None:
                        self._logger.debug(folder_name + " Folder not found adding new folder")
                        root_folder.createFolder(folder_name)
                    else:
                        self._logger.debug(folder_name + " already exist so skipping.....")
            return folder_name
        except Exception as err:
            self._logger.error(err)
            return False


    def upload_file(self,file_name,alfresco_dirctory_name,directory_name='',overwrite_flag = False):

        try:

            root=self.get_root_directory()
            root_folder = self.get_folder_instance(root,alfresco_dirctory_name)
            file_content = open(file_name, 'rb')
            storing_file_name = ntpath.basename(file_name)

            if root_folder==False:
                self._logger.error("Some Error occured while getting root node")
                return False
            else:
                if directory_name=='':
                    self._logger.debug("Directory is not defined, Uploading file to root folder")
                    file_already_exist_object = self.check_duplicate_file(root_folder,storing_file_name)
                    if file_already_exist_object:
                        if overwrite_flag:
                            self.delete_file(file_already_exist_object)
                            root_folder.createDocument(storing_file_name, contentFile=file_content)
                        else:
                            self._logger.debug("File already exist but nothing to do it.")
                    else:
                        root_folder.createDocument(storing_file_name, contentFile=file_content)
                else:
                    folder_instance = self.get_folder_instance(root_folder, directory_name)
                    if folder_instance == False:
                        self._logger.error("Some Error occured while getting specified folder node")
                        return False
                    else:
                        if folder_instance == None:
                            self._logger.debug(directory_name + " Folder not found skipping ..")
                            subfolder= self.cre


                        else:

                            self._logger.debug(" uploading file " + storing_file_name + " to " + directory_name)
                            file_already_exist_object = self.check_duplicate_file(folder_instance, storing_file_name)
                            if file_already_exist_object:
                                if overwrite_flag:
                                    self.delete_file(file_already_exist_object)
                                    folder_instance.createDocument(storing_file_name, contentFile=file_content)
                                else:
                                    self._logger.debug("File already exist but nothing to do it.")
                            else:
                                folder_instance.createDocument(storing_file_name, contentFile=file_content)
            return True
        except Exception as err:
            self._logger.error(err)
            return False

    def download_method(self,file_already_exist_object):
        try:
            name_of_file = file_already_exist_object.getName()
            acl=file_already_exist_object.getACL()
            directory_path = os.path.join(root_path, "files")
            if not os.path.isdir(directory_path):
                os.mkdir(directory_path)
            file_path = os.path.join("files", name_of_file)
            complete_path = os.path.join(root_path, file_path)

            o = open(complete_path, 'wb')
            result = file_already_exist_object.getContentStream()
            o.write(result.read())
            result.close()
            o.close()

            return True
        except Exception as err:
            self._logger.error(err)
            return False

    def download_file(self,file_name,alfresco_dirctory_name,directory_name=''):

        try:
            root = self.get_root_directory()
            root_folder= self.get_folder_instance(root,alfresco_dirctory_name)

            storing_file_name = ntpath.basename(file_name)
            if root_folder==False:
                self._logger.error("Some Error occured while getting root node")
                return False
            else:
                if directory_name=='':
                    self._logger.debug("Directory is not defined, Downloading file from root folder")
                    file_already_exist_object = self.check_duplicate_file(root_folder, storing_file_name)
                    if file_already_exist_object:
                        status=self.download_method(file_already_exist_object)
                        return status

                    else:
                        self._logger.debug(storing_file_name + "File not found for download.")
                else:

                    folder_instance = self.get_folder_instance(root_folder, directory_name)
                    if folder_instance:
                        file_object = self.check_duplicate_file(folder_instance,storing_file_name)
                        if file_object:
                            status=self.download_method(file_object)
                            return status
                        else:
                            self._logger.debug(storing_file_name + "File not found for download.")
                    else:
                        self._logger.debug(directory_name + " not found.")
            return True
        except Exception as err:
            self._logger.error(err)
            return False

    def check_duplicate_file(self,folder_path,file_name):

        try:
            children = folder_path.getChildren()
            file_object = None
            for child in children:
                each_file_name = child.name
                if each_file_name == file_name:
                    file_object = child
                    break
            return file_object
        except Exception as err:
            self._logger.error(err)
            return False

    def delete_file(self,file_object):

        try:
            file_object.delete()
            return True
        except Exception as err:
            self._logger.error(err)
            return False

    def download_links(self,main_directory, sub_directory):
        try:
            root_folder = self.get_root_directory()
            folder_instance = self.get_folder_instance(root_folder,main_directory)
            sub_insttance=self.get_folder_instance(folder_instance,sub_directory)
            sub_insttance.getDescendantsLink()
        except Exception as e:
            self._logger.error(e)

    def delete_complete_folder(self,folder_name):

        try:
            root_folder = self.get_root_directory()
            if root_folder==False:
                self._logger.error("Some Error occured while getting root node")
                return False
            else:
                folder_instance = self.get_folder_instance(root_folder,folder_name)
                if folder_instance==False:
                    self._logger.error("Some Error occured while getting specified folder node")
                    return False
                else:
                    if folder_instance==None:
                        self._logger.debug(" Folder not found so skipping delete process ... ")
                    else:
                        self._logger.debug("Completely deleting folder " + folder_name)
                        folder_instance.deleteTree()
            return True

        except Exception as err:
            self._logger.error(err)
            return False

