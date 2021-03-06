import unittest
from GRID_PiCaS_Launcher import get_picas_credentials as gpc
from GRID_PiCaS_Launcher.get_token_field import get_token_field
from GRID_PiCaS_Launcher.set_token_field import set_token_field
from GRID_PiCaS_Launcher.set_token_field import main as set_token_main
from GRID_PiCaS_Launcher.update_token_status import update_status
import os, sys
from time import sleep
from GRID_PiCaS_Launcher import couchdb
from GRID_PiCaS_Launcher.tok_to_bash import export_tok_keys

from GRID_PiCaS_Launcher.picas.actors import RunActor
from GRID_PiCaS_Launcher.picas.clients import CouchClient
from GRID_PiCaS_Launcher.picas.iterators import BasicViewIterator
from GRID_PiCaS_Launcher.picas.modifiers import BasicTokenModifier
from GRID_PiCaS_Launcher.picas.modifiers import NestedTokenModifier
from GRID_PiCaS_Launcher.picas.executers import execute

from Launch import ExampleActor


class TestActor(RunActor):
    def __init__(self, iterator, modifier):
        self.iterator = iterator
        self.modifier = modifier
        self.client = iterator.client

    def process_token(self, key, token):
        raise Exception(key, token)


class Launchtest(unittest.TestCase):
    _multiprocess_shared_ = True

    def setUp(self):
        vers = str(sys.version_info[0]) + "." + str(sys.version_info[1])
        if vers == "2.6":
            vers = "2.6.0"
        self.t_type = "travis_ci_test" + vers
        pc = gpc.PicasCred()
        creds = pc.return_credentials()
        self.usr = creds["user"]
        self.pwd = creds["password"]
        self.dbn = "sksp_unittest"
        sys.argv = ["dummy", self.dbn, self.usr, self.pwd]
        self.token = "travis_getSBX_test" + vers
        server = couchdb.Server("https://picas-lofar.grid.surfsara.nl:6984")
        self.client = CouchClient(
            url="https://picas-lofar.grid.surfsara.nl:6984",
            db=self.dbn,
            username=self.usr,
            password=self.pwd,
        )
        server.resource.credentials = (self.usr, self.pwd)
        self.db = server[self.dbn]
        tok = {"type": self.token}
        vers = ".".join([str(i) for i in sys.version_info])
        tok["_id"] = self.token
        if "_attachments" in tok.keys():
            _ = tok.pop("_attachments")
        self.db.update([tok])
        set_token_field(self.token, "lock", 0, pc)
        set_token_field(self.token, "string1", "1234", pc)
        set_token_main(self.token, "string1", "1234", self.dbn, self.usr, self.pwd)
        set_token_main(self.token, "string1", "1234")
        set_token_field(self.token, "done", 0, pc)
        update_status(self.dbn, self.usr, self.pwd, self.token, "todo")
        set_token_field(
            self.token,
            "SBXloc",
            "https://home.strw.leidenuniv.nl/~apmechev/sandbox_travis.tar",
            pc,
        )
        self.modifier = BasicTokenModifier()
        iterator = BasicViewIterator(self.client, self.token + "/todo", self.modifier)
        self.TestActor = TestActor(iterator, self.modifier)
        self.Ex = ExampleActor(iterator, self.modifier)
        self.nestedmodifier = NestedTokenModifier()

    def find_and_delete(self, string):
        for att in self.db[self.token]["_attachments"]:
            if string in att:
                self.db.delete_attachment(self.db[self.token], att)

    def tearDown(self):
        pc = gpc.PicasCred(usr=self.usr, dbn=self.dbn, pwd=self.pwd)
        set_token_field(self.token, "lock", 0, pc)
        set_token_field(self.token, "done", 0, pc)
        set_token_field(self.token, "status", "todo", pc)
        set_token_field(self.token, "hostname", "", pc)
        self.client.modify_token(
            self.modifier.add_output(self.db[self.token], {"output": 0})
        )
        self.assertTrue(get_token_field(self.token, "output", pc) == 0)
        set_token_field(self.token, "string1", "1234", pc)
        self.find_and_delete("png")
        self.client.modify_token(self.modifier.unlock(self.db[self.token]))
        self.client.modify_token(self.modifier.unclose(self.db[self.token]))
        update_status(self.dbn, self.usr, self.pwd, self.token, "done")

    def test_lock_token(self):
        pc = gpc.PicasCred(usr=self.usr, pwd=self.pwd, dbn=self.dbn)
        self.assertTrue(get_token_field(self.token, "lock", pc) == 0)
        try:
            self.TestActor.run()
        except Exception as e:
            self.assertTrue(e.args[0] == self.token)
            self.key = e.args[0]
            self.tok = e.args[1]
        self.assertTrue(get_token_field(self.token, "lock", pc) > 0)
        set_token_field(self.token, "lock", 0, pc)
        self.nestedmodifier.lock(self.token, self.client.db)
        self.assertTrue(get_token_field(self.token, "lock", pc) > 0)
        self.nestedmodifier.unlock(self.token, self.client.db)
        self.assertTrue(get_token_field(self.token, "lock", pc) == 0)
        self.nestedmodifier.close(self.token, self.client.db)
        self.assertTrue(get_token_field(self.token, "done", pc) > 0)
        #        self.nestedmodifier.add_output(self.token, self.client.db, 12) #This doesn't work??
        #        self.assertTrue(get_token_field(self.token,'output', pc)==12)
        self.nestedmodifier.set_error(self.token, self.client.db)
        self.assertTrue(get_token_field(self.token, "done", pc) == -1)
        self.assertTrue(get_token_field(self.token, "lock", pc) == -1)
        self.nestedmodifier.unclose(self.token, self.client.db)
        self.assertTrue(get_token_field(self.token, "done", pc) == 0)

    def test_failed_sbx(self):
        pc = gpc.PicasCred(usr=self.usr, dbn=self.dbn, pwd=self.pwd)
        set_token_field(
            self.token,
            "SBXloc",
            "ftp://ftp.strw.leidenuniv.nl/pub/apmechev/travis_ci_tests/sanddbox_travis.tar",
            pc,
        )
        tok = self.db[self.token]
        try:
            self.Ex.process_token(self.token, tok)
        except Exception as e:
            self.assertTrue(str(e) == "Sandbox failed to download!")

    def test_missing_tokvar(self):
        from GRID_PiCaS_Launcher.tok_to_bash import export_tok_keys

        pc = gpc.PicasCred(usr=self.usr, pwd=self.pwd, dbn=self.dbn)
        try:
            export_tok_keys("xtokvar.json", {"_id": self.token})
        except Exception as e:
            self.assertTrue("tokvar read error" in str(e))
            self.assertTrue(get_token_field(self.token, "output", pc) == -2)

    def test_failed_sbx(self):
        tok = self.db[self.token]
        _ = tok.pop("string1")
        self.db.update([tok])
        try:
            self.Ex.process_token(self.token, tok)
        except Exception as e:
            print(str(e))

    def test_scrub(self):
        pc = gpc.PicasCred(usr=self.usr, pwd=self.pwd, dbn=self.dbn)
        scrubs = get_token_field(self.token, "scrub_count", pc)
        self.client.modify_token(self.modifier.scrub(self.db[self.token]))
        self.assertTrue(
            scrubs + 1 == int(get_token_field(self.token, "scrub_count", pc))
        )
        _ = self.nestedmodifier.scrub(self.token, self.client.db)
        self.assertTrue(
            scrubs + 2 == int(get_token_field(self.token, "scrub_count", pc))
        )

        set_token_field(self.token, "scrub_count", scrubs, pc)

    def test_uploadpng(self):
        self.Ex.database = "sksp_unittest"
        self.Ex.user = self.usr
        self.Ex.password = self.pwd
        self.Ex.run()
        #        self.assertEquals(os.environ['SIMG'].split('/')[-1],'lofar@{0}.sif'.format(os.environ['SIMG_COMMIT']))
        for att in self.db[self.token]["_attachments"]:
            if "png" in att:
                return
        raise Exception("test.png was not attached to the Token!")
